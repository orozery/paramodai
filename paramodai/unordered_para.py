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

from itertools import permutations
from paramodai.clause import Clause
from paramodai.literal import Literal
from paramodai.atom import Atom


class UnorderedParamodulator(object):

    def __init__(self, conseq_finder):
        self._conseq_finder = conseq_finder
        self._breaked_clause_cache = {}

    @property
    def _clauses(self):
        return self._conseq_finder._clauses

    def apply_rules(self, c):
        for sign, s, t, gamma, delta in self.break_max_lit(c):

            for c2 in self._clauses[:]:
                if c == c2:
                    continue

                for sign2, s2, t2, gamma2, delta2 in self.break_max_lit(c2):
                    if not sign and not sign2:
                        self._apply_right_superposition(
                            gamma, s, t, delta, gamma2, s2, t2, delta2)
                        self._apply_right_superposition(
                            gamma2, s2, t2, delta2, gamma, s, t, delta)
                    elif not sign and sign2:
                        self._apply_left_superposition(
                            gamma2, s2, t2, delta2, gamma, s, t, delta)
                    elif sign and not sign2:
                        self._apply_left_superposition(
                            gamma, s, t, delta, gamma2, s2, t2, delta2)

            if sign:
                self._apply_equality_resolution(gamma, s, t, delta)
            else:
                for l in delta:
                    for s2, t2 in permutations(l.terms):
                        self._apply_equality_factoring(
                            gamma, s, t, s2, t2, delta - {l})

    def _add_conseq(self, c):
        # print "conseq", c
        if c in [True, False]:
            return
        if len(c) > self._conseq_finder.max_clause_size:
            return
        if c.rank > self._conseq_finder.max_clause_rank:
            return
        self._conseq_finder.add_to_worklist(c)

    def _apply_right_superposition(
            self, gamma1, s, t, delta1, gamma2, l, r, delta2):
        locs = s.subterm_locs.get(l)
        if not locs:
            return
        common_lits = gamma1 | gamma2 | delta1 | delta2
        if len(common_lits) > self._conseq_finder.max_clause_size:
            return

        for loc in locs:
            new_lit = Literal.get(Atom.get(s.replace(loc, r), t))
            # print "right", gamma1, s, t, delta1, gamma2, l, r, delta2
            self._add_conseq(Clause.get(
                common_lits | {new_lit}))

    def _apply_left_superposition(
            self, gamma1, s, t, delta1, gamma2, l, r, delta2):
        locs = s.subterm_locs.get(l)
        if not locs:
            return
        common_lits = gamma1 | gamma2 | delta1 | delta2
        if len(common_lits) > self._conseq_finder.max_clause_size:
            return

        for loc in locs:
            new_lit = Literal.get(Atom.get(s.replace(loc, r), t), True)
            # print "left", gamma1, s, t, delta1, gamma2, l, r, delta2
            self._add_conseq(Clause.get(
                common_lits | {new_lit}))

    def _apply_equality_resolution(self, gamma, s, t, delta):
        if s != t:
            return

        # print "resolution", gamma, s, t, delta
        self._add_conseq(Clause.get(gamma | delta))

    def _apply_equality_factoring(self, gamma, s1, t1, s2, t2, delta):
        if s1 != s2:
            return

        new_pos_lit = Literal.get(Atom.get(s1, t2))
        new_neg_lit = Literal.get(Atom.get(t1, t2), True)

        # print "factoring", gamma, s1, t1, s2, t2, delta
        self._add_conseq(Clause.get(
            gamma | delta | {new_pos_lit, new_neg_lit}))

    def break_max_lit(self, c):
        value = self._breaked_clause_cache.get(c, None)
        if value is None:
            value = self._break_max_lit(c)
            self._breaked_clause_cache[c] = value
        return value

    @staticmethod
    def _break_max_lit(c):
        temp_res = []
        for l in c:
            s, t = l.terms
            for i in xrange(2):
                temp_res.append((l.sign, s, t, c.literals - {l}))
                s, t = t, s

        res = []
        for sign, s, t, other_lits in temp_res:
            gamma = {l for l in other_lits if l.sign}
            delta = other_lits - gamma
            res.append((sign, s, t, gamma, delta))

        return res
