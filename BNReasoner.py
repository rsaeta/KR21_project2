import pandas as pd
from functools import partial
from typing import List
from typing import Union
from BayesNet import BayesNet
import itertools
from copy import deepcopy


class BNReasoner:
    def __init__(self, net: Union[str, BayesNet]):
        """
        :param net: either file path of the bayesian network in BIFXML format or BayesNet object
        """
        if type(net) == str:
            # constructs a BN object
            self.bn = BayesNet()
            # Loads the BN from an BIFXML file
            self.bn.load_from_bifxml(net)
        else:
            self.bn = net

    def __get_leaves(self, exclude=None) -> List[str]:
        exclude = set() if exclude is None else exclude
        return [v for v in self.bn.get_all_variables() 
                        if len(self.bn.get_children(v)) == 0]

    @staticmethod
    def has_path(bn: BayesNet, x: str, Y: set[str]) -> bool:
        """
        Determines whether there is a path from x to any element in Y.
        Simple BFS
        """
        visited = [x]
        while len(visited) > 0:
            node = visited.pop(0)
            children = bn.get_children(node)
            if any(y in children for y in Y):
                return True
            visited.extend(children)
        return False

    @staticmethod
    def disconnected(bn: BayesNet, X: set[str], Y: set[str]) -> bool:
        for x in X:
            if BNReasoner.has_path(bn, x, Y):
                return False
        for y in Y:
            if BNReasoner.has_path(bn, y, X):
                return False
        return True

    @staticmethod
    def __prune_variable(cpt: pd.DataFrame, var, pr: float) -> pd.DataFrame:
        cpt.loc[cpt[var] == True, 'p'] = cpt[cpt[var] == True].p.multiply(pr)
        cpt.loc[cpt[var] == False, 'p'] = cpt[cpt[var] == False].p.multiply(1-pr)
        all_other_vars = [col for col in cpt.columns if col not in [var, 'p']]
        cpt = cpt.groupby(all_other_vars, as_index=False).sum()
        del cpt[var]
        return cpt

    def num_deps(self, x):
        return len(self.bn.get_cpt(x).columns)-2

    def _get_default_ordering(self, deps):
        return deps

    def __get_minfill(self, graph: BayesNet, vars: set[str]):
        graph.get_interaction_graph()
        pass

    def get_minfill_orering(self, vars):
        bn_copy = deepcopy(self.bn)
        self.__get_minfill(bn_copy, vars)
    
    def get_ordered(self, deps):
        """
        This can call any number of heuristics-based implementations that
        order the dependencies of a variable in a particular order. For now
        it just returns the same ordering as given.
        """
        return self._get_default_ordering(deps)

    def _pr(self, x: str):
        """
        Computes probability of x Pr(x) in graph by marginalizing on 
        dependencies
        """
        cpt = self.bn.get_cpt(x)
        deps = [col for col in cpt.columns if col not in ['p', x]]
        if len(deps) == 0:
            return cpt[cpt[x] == True].p.values[0]
        cpt = cpt.copy()
        deps = self.get_ordered(deps)
        for dep in deps:
            pr_dep = self._pr(dep)
            cpt = BNReasoner.__prune_variable(cpt, dep, pr_dep)
        return cpt[cpt[x] == True].p.values[0]

    def prune(self, Q: set[str], e: pd.Series):
        """
        Given a set of query variables Q and evidence e, node- and edge-prune the 
        Bayesian network s.t. queries of the form P(Q|E) can still be correctly 
        calculated. (3.5 pts)
        """
        e_vars = set(e.index)
        # Delete all edges outgoing from evidence e and replace with reduced factor
        for e_var in e_vars:
            children = self.bn.get_children(e_var)
            for child in children:
                self.bn.del_edge((e_var, child))
        # ignore_vars = ['p', *(list(Q.union(E)))]
        # breakpoint()
        # for q in Q.union(E):
        #     cpt = self.bn.get_cpt(q)
        #     deps = [col for col in cpt.columns if col not in ignore_vars]
        #     deps = self.get_ordered(deps)
        #     for dep in deps:
        #         pr = self._pr(dep)
        #         cpt = self.__prune_variable(cpt, dep, pr)
        #         self.bn.update_cpt(q, cpt)
        #     self.bn.update_cpt(q, cpt)
        # rem_nodes = set(self.bn.get_all_variables()) - Q
        # for node in rem_nodes:
        #     self.bn.del_var(node)

    @staticmethod
    def leaves(bn: BayesNet) -> set[str]:
        vars = bn.get_all_variables()
        ls = set()
        for v in vars:
            if len(bn.get_children(v)) == 0:
                ls.add(v)
        return ls

    def dsep(self, X: set[str], Y: set[str], Z: set[str]) -> bool:
        """
        Given three sets of variables X, Y, and Z, determine whether X is d-separated 
        of Y given Z. (4pts)
        """
        bn = deepcopy(self.bn)
        breakpoint()
        while True:
            leaves = BNReasoner.leaves(bn) - X.union(Y).union(Z)
            had_leaves = bool(len(leaves))
            zout_edges = []
            for z in Z:
                zout_edges.extend((z, child) for child in bn.get_children(z))
            had_edges = bool(len(zout_edges))
            if not had_edges and not had_leaves:
                break
            for edge in zout_edges:
                bn.del_edge(edge)
            for leaf in leaves:
                bn.del_var(leaf)
        return BNReasoner.disconnected(bn, X, Y)

    def independent(self, X, Y, Z):
        """
        Independence: Given three sets of variables X, Y, and Z, determine whether X
        is independent of Y given Z. (Hint: Remember the connection between d-separation 
        and independence) (1.5pts)

        TODO: Upate that it also checks other independencies
        """
        return self.dsep(X, Y, Z)
    
    def _compute_new_cpt(self, factor, x, which):
        """
        Given a factor and a variable X, compute the CPT in which X is either summed-out or maxed-out. (3pts)
        """
        factor_table = self.bn.get_cpt(factor)

        f = pd.DataFrame(columns = factor_table.columns)
        f["p"]= []
        del f[x]

        l = [False, True]
        instantiations = [list(i) for i in itertools.product(l, repeat = len(factor_table.columns) - 2)]

        Y = factor_table.columns
        count = 0

        for inst in instantiations:
            inst_dict = {}
            inst_list = []
            for j in range((len(factor_table.columns) - 2)):
                inst_dict[Y[j]] = inst[j]
                inst_list.append(inst[j])
            inst_series = pd.Series(inst_dict)
            comp_inst = self.bn.get_compatible_instantiations_table(inst_series, self.bn.get_cpt(factor))
            if which == 'max':
                new_p = comp_inst.p.max()  
            elif which == 'sum':  
                new_p = comp_inst.p.sum()
            inst_list.append(new_p)
            f.loc[count] = inst_list

            count += 1 

        print(f)

        return(f)

    def marginalize(self, factor, x):
        """
        Given a factor and a variable X, compute the CPT in which X is summed-out. (3pts)
        """
        return self._compute_new_cpt(factor, x, 'sum')
        

    def maxing_out(self, factor, x):
        """
        Given a factor and a variable X, compute the CPT in which X is maxed-out. Remember
        to also keep track of which instantiation of X led to the maximized value. (5pts)
        
        TODO: Keep track of which value of X this comes from
        """
        return self._compute_new_cpt(factor, x, 'max')

    def factor_mult(self, factor_f, factor_g):
        """
        Given two factors f and g, compute the multiplied factor h=fg. (5pts)
        """
        factor_table_f = self.bn.get_cpt(factor_f)
        factor_table_g = self.bn.get_cpt(factor_g)
        print(factor_table_f)
        print(factor_table_g)
        
        X = pd.DataFrame(columns = factor_table_f.columns)
        Y = pd.DataFrame(columns = factor_table_g.columns)
        
        Z = pd.merge(X,Y)

        l = [False, True]
        instantiations = [list(i) for i in itertools.product(l, repeat = len(Z.columns) - 1)]

        inst_df = pd.DataFrame(instantiations, columns= Z.columns[:-1])

        Z = Z.merge(inst_df, how='right')
        
        
        for i in range(len(inst_df)):
            # for j in range(inst_df):
            f = {}
            g = {} 
            for variable in inst_df.columns:
                if variable in factor_table_f.columns:
                    f[variable] = inst_df[variable][i]
                if variable in factor_table_g.columns:
                    g[variable] = inst_df[variable][i]
            
            f_series = pd.Series(f)
            g_series = pd.Series(g)

            comp_inst_f = self.bn.get_compatible_instantiations_table(f_series, self.bn.get_cpt(factor_f))
            comp_inst_g = self.bn.get_compatible_instantiations_table(g_series, self.bn.get_cpt(factor_g))
            value = comp_inst_f.p.values[0] * comp_inst_g.p.values[0]
            
            Z.at[i,'p'] = value 
        print(Z)
        return Z

    def variable_elimination(self, X):
        """
        Variable Elimination: Sum out a set of variables by using variable elimination.
        (5pts)

        set X contains all the variables to eliminate via summing out
        """

    def min_degree_ordering(self, X):
        """Given a set of variables X in the Bayesian network, 
        compute a good ordering for the elimination of X based on the min-degree heuristics (2pts) 
        and the min-fill heuristics (3.5pts). (Hint: you get the interaction graph ”for free” 
        from the BayesNet class.)"""
        graph = self.bn.get_interaction_graph()
        

        pass
        
    def lowest_degree(self, graph, X):
        lowest_degree = 100
        name = "test" 

        for i in X:
            value = graph.degree[i]
            print(value)
            if value < lowest_degree:
                lowest_degree = value
                name = i 
        return name 


    def marginal_distribution(self, Q, e):
        """Given query variables Q and possibly empty evidence e, 
        compute the marginal distribution P(Q|e). Note that Q is a subset of 
        the variables in the Bayesian network X with Q ⊂ X but can also be Q = X. (2.5pts)"""

        # calculation of joint marginal 
        # joint marginal by chain rule
        Z = Q.append(e)
    
        #sum out Q, to calculate Pr(e) 

        #Compute p(Q|e) = joint marginal/pr(e)


def test_prune(reasoner: BNReasoner):
    vars = reasoner.bn.get_all_variables()
    vars = sorted(vars, key=reasoner.num_deps)
    pre_prune = reasoner._pr(vars[4])
    reasoner.prune(set(vars[:4]), set(vars[-1:]))
    assert pre_prune == reasoner._pr(vars[4])


def test_dsep():
    reasoner = BNReasoner('testing/lecture_example3.BIFXML')
    assert reasoner.dsep(set(['Visit to Asia?', 'Smoker?']), set(['Dyspnoea?', 'Positive X-Ray?']), set(['Bronchitis?', 'Tuberculosis or Cancer?']))
    assert reasoner.dsep(set(['Tuberculosis?', 'Lung Cancer?']), set(['Bronchitis?']), set(['Positive X-Ray?']))
    assert not reasoner.dsep(set(['Positive X-Ray?']), set(['Smoker?']), set(['Dyspnoea?', 'Lung Cancer?']))


def main():
    reasoner = BNReasoner('testing/lecture_example.BIFXML')
    reasoner.min_degree(["Wet Grass?", "Sprinkler?", "Slippery Road?", "Rain?", "Winter?"])


if __name__ == '__main__':
    main()
