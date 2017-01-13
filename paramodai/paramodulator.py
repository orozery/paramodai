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
from paramodai.literal import Literal, TrueLiteral, FalseLiteral
from paramodai.atom import Atom


class Paramodulator(object):

    def __init__(self, conseq_finder):
        self._conseq_finder = conseq_finder
        self._breaked_clause_cache = {}

    @property
    def _clauses(self):
        return self._conseq_finder._clauses

    def apply_rules(self, c):
        contains_name_to_kill = self._conseq_finder.name_to_kill in c.names
        for sign, s, t, gamma, delta in self.break_max_lit(c):

            for c2 in self._clauses[:]:
                if (not contains_name_to_kill and
                        not self._conseq_finder.name_to_kill in c2.names):
                    continue

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
        if not c.is_ground:
            return
        if len(c) > self._conseq_finder.max_clause_size:
            return
        if c.rank > self._conseq_finder.max_clause_rank:
            return
        self._conseq_finder.add_to_worklist(c)

    def _apply_right_superposition(
            self, gamma1, s, t, delta1, gamma2, l, r, delta2):
        for subterm, locs in s.subterm_locs.iteritems():
            if subterm.is_var:
                continue

            res = subterm.unify(l)
            if not res:
                continue

            g1, s1, t1, d1 = self._assign(
                res[0], gamma1, s, t, delta1)
            g2, l2, r2, d2 = self._assign(
                res[1], gamma2, l, r, delta2)

            if None in [g1, d1, g2, d2]:
                continue

            lit1 = Literal.get(Atom.get(s1, t1))
            lit2 = Literal.get(Atom.get(l2, r2))

            if {TrueLiteral, FalseLiteral} & {lit1, lit2}:
                continue

            if (not self._is_term_gt(l2, r2) or
                    not self._is_term_gt(s1, t1) or
                    not self._is_term_gt_set(l2, g2) or
                    not self._is_term_gt_set(s1, g1) or
                    not self._is_literal_gt_set(lit2, d2) or
                    not self._is_literal_gt_set(lit1, d1)):
                continue

            for loc in locs:
                new_lit = Literal.get(Atom.get(s1.replace(loc, r2), t1))
                # print "right", gamma1, s, t, delta1, gamma2, l, r, delta2
                self._add_conseq(Clause.get(g1 | g2 | d1 | d2 | {new_lit}))

    def _apply_left_superposition(
            self, gamma1, s, t, delta1, gamma2, l, r, delta2):
        for subterm, locs in s.subterm_locs.iteritems():
            if subterm.is_var:
                continue

            res = subterm.unify(l)
            if not res:
                continue

            g1, s1, t1, d1 = Paramodulator._assign(
                res[0], gamma1, s, t, delta1)
            g2, l2, r2, d2 = Paramodulator._assign(
                res[1], gamma2, l, r, delta2)

            if None in [g1, d1, g2, d2]:
                continue

            lit1 = Literal.get(Atom.get(s1, t1), True)
            lit2 = Literal.get(Atom.get(l2, r2))

            if (not self._is_term_gt(l2, r2) or
                    not self._is_term_gt(s1, t1) or
                    not self._is_term_gt_set(l2, g2) or
                    not self._is_literal_gt_set(lit2, d2) or
                    not self._is_literal_gte_set(lit1, g1 | d1)):
                continue

            for loc in locs:
                new_lit = Literal.get(Atom.get(s1.replace(loc, r2), t1), True)
                # print "left", gamma1, s, t, delta1, gamma2, l, r, delta2
                self._add_conseq(Clause.get(g1 | g2 | d1 | d2 | {new_lit}))

    def _apply_equality_resolution(self, gamma, s, t, delta):
        res = s.unify(t)
        if not res:
            return
        g, s, t, d = Paramodulator._assign(res[0], gamma, s, t, delta)
        if None in [g, d]:
            return
        g, s, t, d = Paramodulator._assign(res[1], g, s, t, d)
        if None in [g, d]:
            return

        lit = Literal.get(Atom.get(s, t))

        if lit is FalseLiteral:
            print gamma, s, t, delta

        if lit is not TrueLiteral and not self._is_literal_gte_set(lit, g | d):
            return

        # print "resolution", gamma, s, t, delta
        self._add_conseq(Clause.get(g | d))

    def _apply_equality_factoring(self, gamma, s1, t1, s2, t2, delta):
        res = s1.unify(s2)
        if not res:
            return
        g, s1, t1, s2, t2, d = Paramodulator._assign(
            res[0], gamma, s1, t1, s2, t2, delta)
        if None in [g, d]:
            return
        g, s1, t1, s2, t2, d = Paramodulator._assign(
            res[1], g, s1, t1, s2, t2, d)
        if None in [g, d]:
            return

        lit1 = Literal.get(Atom.get(s1, t1))
        lit2 = Literal.get(Atom.get(s2, t2))

        if TrueLiteral in [lit1, lit2]:
            return

        if (not self._is_term_gt(s1, t1) or
                not self._is_term_gt_set(s1, g) or
                not self._is_literal_gte_set(lit1, d | {lit2})):
            return

        new_pos_lit = Literal.get(Atom.get(s1, t2))
        new_neg_lit = Literal.get(Atom.get(t1, t2), True)

        # print "factoring", gamma, s1, t1, s2, t2, delta
        self._add_conseq(Clause.get(g | d | {new_pos_lit, new_neg_lit}))

    def _compare_terms(self, t1, t2):
        if t1.is_ground and t2.is_ground:
            return self._conseq_finder.compare_terms(t1, t2)

    def _compare_literals(self, l1, l2):
        if l1.is_ground and l2.is_ground:
            return self._conseq_finder.compare_literals(l1, l2)

    def _is_term_gt(self, t1, t2):
        res = self._compare_terms(t1, t2)
        return res is None or res > 0

    def _is_literal_gt(self, l1, l2):
        res = self._compare_literals(l1, l2)
        return res is None or res > 0

    def _is_literal_gte(self, l1, l2):
        res = self._compare_literals(l1, l2)
        return res is None or res >= 0

    def _is_term_gt_set(self, t, lit_set):
        if not t.is_ground:
            return True
        terms = set()
        for l in lit_set:
            terms |= set(l.terms)
        for t2 in terms:
            if not self._is_term_gt(t, t2):
                return False
        return True

    def _is_literal_gt_set(self, l, lit_set):
        if not l.is_ground:
            return True
        for l2 in lit_set:
            if not self._is_literal_gt(l, l2):
                return False
        return True

    def _is_literal_gte_set(self, l, lit_set):
        if not l.is_ground:
            return True
        for l2 in lit_set:
            if not self._is_literal_gte(l, l2):
                return False
        return True

    def break_max_lit(self, c):
        value = self._breaked_clause_cache.get(c, None)
        if value is None:
            value = self._break_max_lit(c)
            self._breaked_clause_cache[c] = value
        return value

    def _break_max_lit(self, c):
        ground_lits = {l for l in c if l.is_ground}
        non_ground_lits = c.literals - ground_lits

        temp_res = []

        for l in non_ground_lits:
            for s, t in permutations(l.terms):
                temp_res.append((l.sign, s, t, c.literals - {l}))

        if ground_lits:
            l = self._conseq_finder.get_max_literal(ground_lits)
            s, t = l.terms
            if self._conseq_finder.compare_terms(s, t) < 0:
                s, t = t, s
            if l.sign or self._is_term_gt_set(
                    s, {l2 for l2 in ground_lits if l2.sign}):
                temp_res.append((l.sign, s, t, c.literals - {l}))

        res = []
        for sign, s, t, other_lits in temp_res:
            gamma = {l for l in other_lits if l.sign}
            delta = other_lits - gamma
            res.append((sign, s, t, gamma, delta))

        return res

    @staticmethod
    def _assign(value, *params):
        if value.is_var:
            for p in params:
                yield p
            return

        for p in params:
            if isinstance(p, (set, frozenset)):
                res = {x.assign(value) for x in p}
                if TrueLiteral in res:
                    yield None
                else:
                    yield {x for x in res if x is not FalseLiteral}
            else:
                yield p.assign(value)
