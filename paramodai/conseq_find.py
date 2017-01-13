# Copyright 2017 Or Ozeri
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from paramodai.term import Term
from paramodai.literal import FalseLiteral, TrueLiteral
from paramodai.clause import Clause
from paramodai.paramodulator import Paramodulator
from paramodai.unordered_para import UnorderedParamodulator
from z3 import unsat, Solver


class EmptyClauseException(Exception):
    pass


class ConsequenceFinder(object):

    PRUNE_THRESHOLD = 100

    def __init__(
            self, state, name_to_kill,
            max_clause_size=2, max_clause_rank=1,
            remove_redundant_clauses=False):
        self.state = state
        self.name_to_kill = name_to_kill
        self.max_clause_size = max_clause_size
        self.max_clause_rank = max_clause_rank
        self.remove_redundant_clauses = remove_redundant_clauses

        if name_to_kill is None:
            self._paramodulator = UnorderedParamodulator(self)
        else:
            self.names_order = Term.BASE_ORDER + [name_to_kill]
            self._compare_terms_cache = {}
            self._compare_literals_cache = {}
            self._compare_clauses_cache = {}
            self._get_max_cache = {}
            self._false_literals_cache = {}

            self._paramodulator = Paramodulator(self)
        # self._orig_clauses = state.clauses.copy()

        # self._base_clauses = self.state.clauses.copy()
        # self._is_base_clause = True
        # self._result_of_base_clauses = set()

        self._clauses = []
        self._worklist = set()
        # self._base_worklist = set()
        self._seen_clauses = set()
        for c in self.state.clauses:
            self.add_to_worklist(c)

        if self.remove_redundant_clauses:
            self._solver = self.state.get_solver()
            self._time_to_prune = len(self) + self.PRUNE_THRESHOLD
            self._pruning_snapshot = self._clauses[:]

    def __len__(self):
        return len(self._clauses)

    def run(self):
        print self.name_to_kill,
        # prev = self.state.clauses.copy()
        if self.remove_redundant_clauses:
            self._remove_redundant_clauses()
        while self._worklist:
            if self.remove_redundant_clauses:
                if len(self) > self._time_to_prune:
                    self._remove_redundant_clauses()
                    self._time_to_prune = len(self) + self.PRUNE_THRESHOLD
                    continue

            c = self._worklist.pop()
            self._paramodulator.apply_rules(c)
        if self.remove_redundant_clauses:
            self._remove_redundant_clauses()
        print ".",
        # new_clauses = self.state.clauses - prev
        # print len(new_clauses),
        # if new_clauses:
        #     print new_clauses.pop()
        # else:
        #     print

    def add_to_worklist(self, c):
        if c is True:
            return
        if not c:
            raise EmptyClauseException()

        if c in self._seen_clauses:
            return

        self._seen_clauses.add(c)

        if self.state.is_subsumed(c):
            return

        # print "new clause", c

        self._worklist.add(c)

        if self.remove_redundant_clauses:
            pos = self._get_clause_position(c)
            self._clauses.insert(pos, c)
        else:
            self._clauses.append(c)
        self.state.clauses.add(c)

    def _get_clause_position(self, c):
        lo = 0
        hi = len(self)
        while lo < hi:
            mid = (lo+hi)/2
            res = self.compare_clauses(c, self._clauses[mid])
            if res > 0:
                lo = mid+1
            else:
                hi = mid-1
        return lo

    def _remove_redundant_clauses(self):
        solver = Solver()
        pos = 0
        n = min(len(self._clauses), len(self._pruning_snapshot))
        for i in xrange(n):
            if self._clauses[pos] != self._pruning_snapshot[pos]:
                break
            solver.add(self._clauses[pos].z3_expr)
            pos += 1

        while pos < len(self._clauses):
            c = self._clauses[pos]
            if len(c) == 1:
                solver.add(c.z3_expr)
                pos += 1
                continue
            solver.push()
            solver.add(c.z3_not_expr)
            # print "----------"
            # print solver
            # print "----------"
            res = solver.check()
            solver.pop()
            if res == unsat:
                self.state.clauses.remove(c)
                self._worklist.discard(c)
                self._clauses.pop(pos)
            else:
                solver.add(c.z3_expr)
                pos += 1

        self._pruning_snapshot = self._clauses[:]

    def _compare_names(self, name1, name2):
        index1 = self.names_order.index(name1)\
            if name1 in self.names_order else -1
        index2 = self.names_order.index(name2)\
            if name2 in self.names_order else -1
        # a tuple name refers to a boolean, thus should have the lowest order
        return cmp((not isinstance(name1, tuple), index1, name1),
                   (not isinstance(name2, tuple), index2, name2))

    def compare_terms(self, t1, t2):
        key = (t1, t2)
        value = self._compare_terms_cache.get(key, None)
        if value is None:
            value = self._compare_terms(t1, t2)
            self._compare_terms_cache[key] = value
            self._compare_terms_cache[(t2, t1)] = value * -1
        return value

    def compare_literals(self, l1, l2):
        key = (l1, l2)
        value = self._compare_literals_cache.get(key, None)
        if value is None:
            value = self._compare_literals(l1, l2)
            self._compare_terms_cache[key] = value
            self._compare_terms_cache[(l2, l1)] = value * -1
        return value

    def compare_clauses(self, c1, c2):
        key = (c1, c2)
        value = self._compare_clauses_cache.get(key, None)
        if value is None:
            value = self._compare_clauses(c1, c2)
            self._compare_clauses_cache[key] = value
            self._compare_clauses_cache[(c2, c1)] = value * -1
        return value

    def get_max(self, s, compare_func):
        key = frozenset(s)
        value = self._get_max_cache.get(key, None)
        if value is None:
            value = self._get_max(s, compare_func)
            self._get_max_cache[key] = value
        return value

    def get_max_literal(self, lits):
        return self.get_max(lits, self.compare_literals)

    def _compare_clauses(self, c1, c2):
        if c1 == c2:
            return 0
        if not c1:
            return 1
        if not c2:
            return -1
        if c1 is True:
            return 1
        if c2 is True:
            return -1
        return self._compare_mul(
            c1.literals, c2.literals, self.compare_literals)

    def _compare_literals(self, l1, l2):
        lit_terms = []
        for l in [l1, l2]:
            terms = l.terms
            if self.compare_terms(*terms) < 0:
                lit_terms.append(terms[::-1])
            else:
                lit_terms.append(terms)

        res = self.compare_terms(lit_terms[0][0], lit_terms[1][0])
        if res != 0:
            return res
        if l1.sign != l2.sign:
            if l1.sign:
                return 1
            else:
                return -1
        return self.compare_terms(lit_terms[0][1], lit_terms[1][1])

    def _compare_terms(self, t1, t2):
        for t in t1.sub_terms:
            if self.compare_terms(t, t2) >= 0:
                return 1
        for t in t2.sub_terms:
            if self.compare_terms(t, t1) >= 0:
                return -1
        name_cmp = self._compare_names(t1.name, t2.name)
        if name_cmp != 0:
            return name_cmp

        if t1.name in Term.MUL_FUNCS:
            return self._compare_mul(
                t1.sub_terms, t2.sub_terms, self.compare_terms)
        else:
            return self._compare_lex(
                t1.sub_terms, t2.sub_terms, self.compare_terms)

    @staticmethod
    def _get_max(s, compare_func):
        res = None
        for x in s:
            if res is None or compare_func(x, res) > 0:
                res = x
        return res

    def _compare_mul(self, s1, s2, compare_func):
        s1 = set(s1)
        s2 = set(s2)

        if s1 == s2:
            return 0

        s3 = s1 & s2
        s1 -= s3
        s2 -= s3

        if not s1 and s2:
            return -1
        if not s2 and s1:
            return 1

        return compare_func(self.get_max(s1, compare_func),
                            self.get_max(s2, compare_func))

    @staticmethod
    def _compare_lex(s1, s2, compare_func):
        for x1, x2 in zip(s1, s2):
            res = compare_func(x1, x2)
            if res != 0:
                return res
        return cmp(len(s1), len(s2))

    def simplify_literal(self, l):
        if self.is_false_literal(l):
            return FalseLiteral
        if self.is_false_literal(~l):
            self.add_clause(Clause.get({l}))
            return TrueLiteral
        return l

    def is_false_literal(self, l):
        value = self._false_literals_cache.get(l, None)
        if value is None:
            value = self._is_false_literal(l)
            self._false_literals_cache[l] = value
        return value

    def _is_false_literal(self, l):
        if l.atom is None:
            return l.sign is False
        self._solver.push()
        self._solver.add(l.z3_expr)
        res = self._solver.check() == unsat
        self._solver.pop()
        return res
