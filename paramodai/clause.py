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

from paramodai.literal import FalseLiteral, TrueLiteral
from itertools import chain, combinations, imap
from z3 import BoolVal, Or, Not, FreshInt, ForAll


class Clause(object):

    __slots__ = ("literals", "_z3_expr", "_z3_not_expr", "_names", "_atomic_names")

    _clauses_cache = {}

    def __init__(self, literals):
        self.literals = literals
        self._names = None
        self._atomic_names = None
        self._z3_expr = None
        self._z3_not_expr = None

    def __repr__(self):
        return " ; ".join(map(repr, self.literals))

    def __or__(self, other):
        return Clause.get(self.literals | other.literals)

    @property
    def names(self):
        if self._names is None:
            self._names = self._get_names()
        return self._names

    @property
    def atomic_names(self):
        if self._atomic_names is None:
            self._atomic_names = self._get_atomic_names()
        return self._atomic_names

    @property
    def rank(self):
        if not self.literals:
            return 0
        return max([l.rank for l in self])

    def remove_literal(self, l):
        if l not in self:
            return self
        return Clause.get(self.literals - {l})

    def subsumes(self, c):
        return self.literals.issubset(c.literals)

    def add_literals(self, *literals):
        return Clause.get(self.literals | set(literals))

    def rename(self, old_name, new_name):
        if old_name not in self.names:
            return self
        return Clause.get({l.rename(old_name, new_name)
                           for l in self.literals})

    def __iter__(self):
        for l in self.literals:
            yield l

    def __len__(self):
        return len(self.literals)

    def simplify(self):
        literals = {l for l in self.literals if l is not FalseLiteral}
        if TrueLiteral in literals:
            return True
        for l in literals:
            if ~l in literals:
                return True
        if len(literals) != len(self.literals):
            return self.get(literals)
        return self

    def _get_names(self):
        names = set()
        for l in self.literals:
            names |= l.names
        return names

    def _get_atomic_names(self):
        atomic_names = set()
        for l in self.literals:
            atomic_names |= l.atomic_names
        return atomic_names

    def iter_subclauses(self):
        return imap(Clause.get,
                    chain.from_iterable(combinations(self.literals, r)
                                        for r in xrange(1, len(self))))

    @property
    def z3_expr(self):
        value = self._z3_expr
        if value is None:
            if not self:
                value = BoolVal(False)
            else:
                unique_var = FreshInt()

                if self.is_ground:
                    sub_exprs = [l.z3_expr for l in self]
                else:
                    sub_exprs = [l.assign_z3_expr(unique_var) for l in self]

                if len(self) == 1:
                    value = sub_exprs[0]
                else:
                    value = Or(*sub_exprs)

                if not self.is_ground:
                    value = ForAll(unique_var, value)
            self._z3_expr = value
        return value

    @property
    def z3_not_expr(self):
        value = self._z3_not_expr
        if value is None:
            value = Not(self.z3_expr)
            self._z3_not_expr = value
        return value

    @property
    def must_keep(self):
        if len(self) != 1:
            return False
        l = list(self)[0]
        for t in l.terms:
            if t.is_const or t.is_stack:
                return True
        return False

    @staticmethod
    def get(literals=set()):
        key = frozenset(literals)
        cache = Clause._clauses_cache
        value = cache.get(key, None)
        if value is None:
            value = Clause(key)
            value = value.simplify()
            cache[key] = value
        return value

    def prime(self):
        return Clause.get({l.prime() for l in self.literals})

    @property
    def pos_lits(self):
        return {l for l in self if not l.sign}

    @property
    def neg_lits(self):
        return {l for l in self if l.sign}

    @property
    def is_ground(self):
        for l in self:
            if not l.is_ground:
                return False
        return True
