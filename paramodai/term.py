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

from z3 import Function, IntSort, Int, BoolVal
import operator

VAR_NAME = "!!x"
DEREF_NAME = "deref"


class Term(object):

    _terms_cache = {}

    BASE_ORDER = ["add", "neg", "mul", DEREF_NAME]

    __slots__ = ("name", "sub_terms", "_z3_expr", "rank", "names",
                 "atomic_names", "subterm_locs", "_replacements_cache")

    MUL_FUNCS = {"add", "mul"}

    Z3_FUNCS = {"add": operator.add,
                "neg": operator.neg,
                "mul": operator.mul,
                "eq": operator.eq,
                "ne": operator.ne,
                "ge": operator.ge,
                "gt": operator.gt,
                "le": operator.le,
                "lt": operator.lt}

    def __init__(self, name, *sub_terms):
        self.name = name
        self.sub_terms = sub_terms
        self._z3_expr = None
        self.subterm_locs = self._get_subterm_locs()
        self._replacements_cache = {}
        self.rank = self._get_rank()
        self.names = self._get_names()
        self.atomic_names = self._get_atomic_names()

    def __repr__(self):
        if self.is_bool:
            return repr(self.name[0])
        if self.is_const:
            return hex(self.name)
        if self.is_atomic:
            return self.name

        sub_reprs = []
        for x in self.sub_terms:
            if (x.name == "add" and
                    self.name in ["mul", "neg"]):
                sub_reprs.append("(%s)" % x)
            else:
                sub_reprs.append("%s" % x)
        sub_reprs = tuple(sub_reprs)

        if self.name == "add":
            return "%s + %s" % sub_reprs
        if self.name == "mul":
            return "%s * %s" % sub_reprs
        if self.name == "neg":
            return "-%s" % sub_reprs
        if self.name == DEREF_NAME:
            return "[%s]" % sub_reprs
        if self.name == "d_tmp":
            return "@[%s]" % sub_reprs
        if self.name == "eq":
            return "%s == %s" % sub_reprs
        if self.name == "ne":
            return "%s != %s" % sub_reprs
        if self.name == "ge":
            return "%s >= %s" % sub_reprs
        if self.name == "gt":
            return "%s > %s" % sub_reprs
        if self.name == "le":
            return "%s <= %s" % sub_reprs
        if self.name == "lt":
            return "%s < %s" % sub_reprs
        else:
            return "%s(%s)" % (self.name, ", ".join(sub_reprs))

    @staticmethod
    def get(name, *sub_terms):
        cache = Term._terms_cache

        if name in Term.MUL_FUNCS:
            sub_terms = tuple(sorted(sub_terms))

        if isinstance(name, bool):
            # to avoid collisions: True == 1, False == 0
            key = name
        else:
            key = (name,) + sub_terms

        value = cache.get(key, None)
        if value is None:
            value = Term(name, *sub_terms)
            # value = value.simplify()
            cache[key] = value

        return value

    def simplify(self):

        if self.name == "add":
            a, b = self.sub_terms
            # if a == ZERO:
            #     return b
            # if b == ZERO:
            #     return a
            # if a.is_const and b.is_const:
            #     return Term.get(a.name + b.name)
            if b.is_const:
                a, b = b, a
            if a.is_const and b.name == "add":
                c, d = b.sub_terms
                if d.is_const:
                    c, d = d, c
                if c.is_const:
                    return Term.get("add", Term.get(a.name + c.name), d)
            if a == b:
                return Term.get("mul", Term.get(2), a)
        elif self.name == "neg":
            a = self.sub_terms[0]
            if a.is_const:
                return Term.get(-a.name)
            if a.name == "neg":
                return a.sub_terms[0]
        elif self.name == "mul":
            if ZERO in self.sub_terms:
                return ZERO
            a, b = self.sub_terms
            if a == ONE:
                return b
            if b == ONE:
                return a
            if a == MINUS_ONE:
                return -b
            if b == MINUS_ONE:
                return -a
            if a.is_const and b.is_const:
                return Term.get(a.name * b.name)
            if b.is_const:
                a, b = b, a
            if a.is_const and b.name == "mul":
                c, d = b.sub_terms
                if d.is_const:
                    c, d = d, c
                    if c.is_const:
                        return Term.get("mul", Term.get(a.name * c.name), d)
            if a.name == "neg" and b.name == "neg":
                return a.sub_terms[0] * b.sub_terms[0]
        return self

    def replace(self, loc, new_term):
        if not loc:
            return new_term

        key = (loc, new_term)
        value = self._replacements_cache.get(key, None)
        if value is None:
            sub_terms = [x for x in self.sub_terms]
            sub_terms[loc[0]] = sub_terms[loc[0]].replace(loc[1:], new_term)
            value = Term.get(self.name, *sub_terms)
            self._replacements_cache[key] = value
        return value

    def assign(self, value):
        if self.is_ground:
            return self
        if self == VAR:
            return value
        return Term.get(self.name, *[t.assign(value) for t in self.sub_terms])

    def unify(self, term):
        if self.is_var:
            if not term.is_ground and term != VAR:
                return
            if term.is_bool or term.is_cmp:
                return
            return term, VAR
        if term.is_var:
            if not self.is_ground and self != VAR:
                return
            if self.is_bool or self.is_cmp:
                return
            return VAR, self
        if self.name is not term.name:
            return
        assert self.arity == term.arity

        sub_res = \
            [t1.unify(t2) for t1, t2 in zip(self.sub_terms, term.sub_terms)]

        if None in sub_res:
            return
        res = []
        for i in xrange(2):
            assignments = {x[i] for x in sub_res if x[i] != VAR}
            if not assignments:
                res.append(VAR)
            else:
                res.append(assignments.pop())
                if assignments:
                    return
        return tuple(res)

    def rename(self, old_name, new_name):
        if old_name not in self.names:
            return self
        sub_terms = [t.rename(old_name, new_name) for t in self.sub_terms]
        name = new_name if self.name == old_name else self.name
        return Term.get(name, *sub_terms)

    def _get_subterm_locs(self):
        subterm_locs = {self: [()]}
        for i, term in enumerate(self.sub_terms):
            for subterm, locs in term.subterm_locs.iteritems():
                for loc in locs:
                    subterm_locs[subterm] = \
                        subterm_locs.get(subterm, []) + [(i,) + loc]
        return subterm_locs

    def _get_names(self):
        names = {self.name}
        for term in self.sub_terms:
            names |= term.names
        return names

    def _get_atomic_names(self):
        if self.is_atomic:
            return {self.name}
        names = set()
        for term in self.sub_terms:
            names |= term.atomic_names
        return names

    def _get_rank(self):
        sub_ranks = [x.rank for x in self.sub_terms]
        if sub_ranks:
            return 1 + max(sub_ranks)
        else:
            return 0

    @property
    def is_const(self):
        return isinstance(self.name, (int, long))

    @property
    def is_atomic(self):
        return not self.sub_terms

    @property
    def arity(self):
        return len(self.sub_terms)

    @property
    def stack_offset(self):
        if self == STACK:
            return 0
        if self.name == "add":
            if self.sub_terms[0] == STACK and self.sub_terms[1].is_const:
                return self.sub_terms[1].name
            if self.sub_terms[1] == STACK and self.sub_terms[0].is_const:
                return self.sub_terms[0].name

    @property
    def is_stack(self):
        return self.stack_offset is not None

    @property
    def is_cmp(self):
        return self.name in ["eq", "ne", "ge", "gt", "le", "lt"]

    @property
    def is_bool(self):
        return isinstance(self.name, tuple)

    @property
    def is_var(self):
        return self.name == VAR_NAME

    @property
    def is_ground(self):
        return VAR_NAME not in self.names

    @property
    def is_reg(self):
        return self.is_atomic and not self.is_const

    @property
    def is_deref(self):
        return self.name == DEREF_NAME

    @property
    def addr(self):
        return self.sub_terms[0]

    @property
    def z3_expr(self):
        expr = self._z3_expr
        if expr is None:
            if self.is_atomic:
                if self.is_const:
                    # expr = IntVal(self.name)
                    expr = Int(str(self.name))
                elif self.is_bool:
                    expr = BoolVal(self.name[0])
                else:
                    expr = Int(self.name)
            else:
                sub_exprs = [x.z3_expr for x in self.sub_terms]
                expr = self._apply_z3_func(*sub_exprs)
            self._z3_expr = expr
        return expr

    def _apply_z3_func(self, *sub_exprs):
        func = self.Z3_FUNCS.get(self.name, None)
        if True or func is None:
            func = Function(
                *([self.name] +
                  [IntSort()] * (self.arity + 1)))
            self.Z3_FUNCS[self.name] = func

        return func(*sub_exprs)

    def assign_z3_expr(self, z3_value):
        if self.is_ground:
            return self.z3_expr
        if self.is_var:
            return z3_value

        assert not self.is_atomic

        sub_exprs = [x.assign_z3_expr(z3_value) for x in self.sub_terms]

        return self._apply_z3_func(*sub_exprs)

    def deref(self):
        return Term.get(DEREF_NAME, self)

    def d_tmp(self):
        return Term.get("d_tmp", self)

    def arg_deref(self):
        return Term.get("!deref", self)

    def __invert__(self):
        if self.is_bool:
            return Term.get((self.name[0] ^ True),)
        if self.name == "eq":
            return Term.get("ne", *self.sub_terms)
        if self.name == "ne":
            return Term.get("eq", *self.sub_terms)
        if self.name == "ge":
            return Term.get("lt", *self.sub_terms)
        if self.name == "gt":
            return Term.get("le", *self.sub_terms)
        if self.name == "le":
            return Term.get("gt", *self.sub_terms)
        if self.name == "lt":
            return Term.get("ge", *self.sub_terms)
        print "Cannot invert term:", self
        raise NotImplementedError()

    def __add__(self, other):
        return Term.get("add", self, other)

    def __sub__(self, other):
        return self + (-other)

    def __neg__(self):
        return Term.get("neg", self)

    def __mul__(self, other):
        return Term.get("mul", self, other)

    def prime(self):
        if self.is_atomic:
            if isinstance(self.name, str) and not self.name.startswith("!"):
                if self.name.endswith("'"):
                    return Term.get(self.name[:-1])
                else:
                    return Term.get(self.name+"'")
            return self
        # if self.name == DEREF_NAME:
        #     return Term.get("d_tmp", *[t.prime() for t in self.sub_terms])
        return Term.get(self.name, *[t.prime() for t in self.sub_terms])

    @property
    def is_prime(self):
        return self.is_reg and self.name.endswith("'")

    def old(self):
        if not isinstance(self.name, str):
            return self
        if self.name.startswith("OLD_"):
            return Term.get(self.name[4:], *self.sub_terms)
        else:
            return Term.get("OLD_" + self.name, *self.sub_terms)

ZERO = Term.get(0)
ONE = Term.get(1)
MINUS_ONE = Term.get(-1)
FALSE = Term.get((False,))
TRUE = Term.get((True,))
STACK = Term.get("!STACK")
VAR = Term.get(VAR_NAME)
