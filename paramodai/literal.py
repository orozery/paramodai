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

class Literal(object):

    _literal_cache = {}

    __slots__ = ("atom", "sign", "_z3_expr")

    def __init__(self, atom, sign=False):
        self.atom = atom
        self.sign = sign
        self._z3_expr = None

    @staticmethod
    def get(atom, sign=False):
        cache = Literal._literal_cache

        key = (atom, sign)
        value = cache.get(key, None)
        if value is None:
            if atom in [True, False]:
                value = Literal.get(None, sign ^ atom)
            elif atom and atom.is_cmp and sign:
                value = Literal.get(~atom)
            else:
                value = Literal(atom, sign)
            cache[key] = value

        return value

    def __invert__(self):
        return Literal.get(self.atom, not self.sign)

    @property
    def z3_expr(self):
        value = self._z3_expr
        if value is None:
            if self.sign:
                value = (self.terms[0].z3_expr !=
                         self.terms[1].z3_expr)
            else:
                value = self.atom.z3_expr
            self._z3_expr = value
        return value

    @property
    def rank(self):
        if self.atom is not None:
            return self.atom.rank
        else:
            return 0

    def assign(self, value):
        if self.is_ground:
            return self
        return Literal.get(self.atom.assign(value), self.sign)

    def assign_z3_expr(self, z3_value):
        if self.is_ground:
            return self.z3_expr

        if self.sign:
            return (self.terms[0].assign_z3_expr(z3_value) !=
                    self.terms[1].assign_z3_expr(z3_value))
        else:
            return (self.terms[0].assign_z3_expr(z3_value) ==
                    self.terms[1].assign_z3_expr(z3_value))

    @property
    def names(self):
        return self.atom.names

    @property
    def atomic_names(self):
        return self.atom.atomic_names

    @property
    def terms(self):
        return self.atom.terms

    def replace(self, loc, subloc, new_term):
        return Literal.get(self.atom.replace(loc, subloc, new_term), self.sign)

    def rename(self, old_name, new_name):
        if old_name not in self.names:
            return self
        return Literal.get(self.atom.rename(old_name, new_name), self.sign)

    @property
    def is_cmp(self):
        return self.atom is not None and self.atom.is_cmp

    @property
    def is_ground(self):
        return self.atom is None or self.atom.is_ground

    def __repr__(self):
        if self.atom is None:
            return repr(self.sign)
        if self.is_cmp:
            return repr(self.atom)
        if self.sign:
            return "%s != %s" % tuple(self.terms)
        else:
            return "%s == %s" % tuple(self.terms)

    def prime(self):
        if self.atom is None:
            return self
        return Literal.get(self.atom.prime(), self.sign)

TrueLiteral = Literal.get(None, True)
FalseLiteral = Literal.get(None, False)
