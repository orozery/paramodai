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

from z3 import BoolVal, simplify
from paramodai.term import TRUE

Z3_FALSE = BoolVal(False)
Z3_TRUE = BoolVal(True)


class Atom(object):

    _atom_cache = {}

    __slots__ = ("terms", "names", "atomic_names", "_z3_expr")

    def __init__(self, *terms):
        assert len(terms) == 2
        self.terms = terms
        self._z3_expr = None
        self.names = self.terms[0].names | self.terms[1].names
        self.atomic_names = (self.terms[0].atomic_names |
                             self.terms[1].atomic_names)

    def simplify(self):
        if self.terms[0] == self.terms[1]:
            return True
        simplified = simplify(self.z3_expr)
        if simplified.eq(Z3_FALSE):
            return False
        if simplified.eq(Z3_TRUE):
            return True
        return self

    def rename(self, old_name, new_name):
        if old_name not in self.names:
            return self
        return Atom.get(*[t.rename(old_name, new_name) for t in self.terms])

    def replace(self, loc, subloc, new_term):
        if loc == 0:
            return Atom.get(self.terms[0].replace(subloc, new_term),
                            self.terms[1])
        elif loc == 1:
            return Atom.get(self.terms[0],
                            self.terms[1].replace(subloc, new_term))
        else:
            return self

    @property
    def z3_expr(self):
        value = self._z3_expr
        if value is None:
            value = (self.terms[0].z3_expr == self.terms[1].z3_expr)
            self._z3_expr = value
        return value

    def __repr__(self):
        if self.is_cmp:
            return repr(self.terms[0])
        return "%s == %s" % tuple(self.terms)

    @property
    def is_cmp(self):
        return self.terms[0].is_cmp

    @property
    def is_ground(self):
        for t in self.terms:
            if not t.is_ground:
                return False
        return True

    @property
    def rank(self):
        return max([t.rank for t in self.terms])

    def assign(self, value):
        if self.is_ground:
            return self
        return Atom.get(*[t.assign(value) for t in self.terms])

    def __invert__(self):
        assert self.is_cmp
        return Atom.get(~self.terms[0], self.terms[1])

    @staticmethod
    def get(*terms):
        cache = Atom._atom_cache

        if terms[1] != TRUE:
            key = tuple(sorted(terms))
            if key != terms:
                return Atom.get(*key)

        value = cache.get(terms, None)
        if value is None:
            value = Atom(*terms)
            value = value.simplify()
            cache[terms] = value

        return value

    def prime(self):
        return Atom.get(*[t.prime() for t in self.terms])
