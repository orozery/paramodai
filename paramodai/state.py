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

from paramodai.clause import Clause
from paramodai.atom import Atom
from paramodai.literal import Literal
from paramodai.term import Term, TRUE, VAR
from paramodai.conseq_find import ConsequenceFinder
from z3 import unsat, Solver, And, Not, sat, FreshBool, Implies
from itertools import product


class AbstractState(object):

    _counter = 0
    MAX_CLAUSE_SIZE = 3
    MAX_CLAUSE_RANK = 10

    __slots__ = "clauses", "_instr"

    def __init__(self, clauses=None):
        if not clauses:
            clauses = set()
        self._instr = None
        self.clauses = clauses

    def __contains__(self, clause):
        return clause in self.clauses

    def is_subsumed(self, c):
        if ((1 << len(c)) - 2) < len(self.clauses):
            for c2 in c.iter_subclauses():
                if c2 in self.clauses:
                    return True
        else:
            for c2 in self.clauses:
                if c2 == c:
                    continue
                if c2.subsumes(c):
                    return True
        return False

    def remove_subsumed_clauses(self):
        subsumed = set()
        for c in self:
            if self.is_subsumed(c):
                subsumed.add(c)
        self.remove_clauses(subsumed)

    def remove_clauses(self, clauses):
        self.clauses.difference_update(clauses)

    def add_clause(self, clause):
        if clause is not True:
            self.clauses.add(clause)

    def copy(self):
        res = AbstractState(self.clauses.copy())
        res._instr = self._instr
        return res

    def __len__(self):
        return len(self.clauses)

    def _iter_eqs(self):
        for c in self:
            if len(c) == 1:
                l = list(c)[0]
                if not l.sign:
                    yield l.terms

    def simplify_term(self, term):
        return term

    # def simplify_term(self, term):
    #     if term.is_const or term.is_stack:
    #         return term
    #
    #     if term.is_atomic:
    #         for t1, t2 in self._iter_eqs():
    #             if t1 == term and (t2.is_const or t2.is_stack):
    #                 return t2
    #             if t2 == term and (t1.is_const or t1.is_stack):
    #                 return t1
    #     else:
    #         sub_terms = [self.simplify_term(x) for x in term.sub_terms]
    #         if term.is_deref:
    #             addr = sub_terms[0]
    #             if addr.is_const:
    #                 return Term.get("glb_%x" % addr.name)
    #             stack_offset = addr.stack_offset
    #             if stack_offset is not None:
    #                 return Term.get("stk_%x" % stack_offset)
    #         return Term.get(term.name, *sub_terms)
    #
    #     return term

    def add_eq(self, term1, term2, sign=False):
        self.add_clause(Clause.get({Literal.get(Atom.get(term1, term2),
                                                sign)}))

    def handle_assertions(self, assertions):
        for cond, term1, term2 in assertions:
            if cond == "eq":
                self.add_eq(term1, term2)
            elif cond == "ne":
                self.add_eq(term1, term2, True)
            elif cond == "le":
                self.add_eq(Term.get("gt", term1, term2), TRUE, True)
            elif cond == "lt":
                self.add_eq(Term.get("ge", term1, term2), TRUE, True)
            else:
                self.add_eq(Term.get(cond, term1, term2), TRUE)

        if self.get_solver().check() == unsat:
            return False

        self.compactify()

        return True

    def handle_assignment(self, dst_term, src_term):
        tmps = []
        dst_rank = dst_term.rank
        if src_term is None:
            if dst_rank > 1:
                dst_term, tmps = self._eval_sub_terms(dst_term)
            self.kill(dst_term)
            for tmp in tmps:
                self.kill(tmp)
            return

        src_rank = src_term.rank

        if src_rank > 1:
            src_term, tmps = self._eval_sub_terms(src_term)
        if dst_rank > 1:
            if src_rank > 0:
                tmp = Term.get("tmp")
                self._handle_simple_assignment(tmp, src_term)
                src_term = tmp
                for tmp in tmps:
                    self.kill(tmp)
            dst_term, tmps = self._eval_sub_terms(dst_term)

        if dst_term.name in src_term.names:
            tmp = Term.get("tmp")
            self._handle_simple_assignment(tmp, src_term)
            src_term = tmp

        self._handle_simple_assignment(dst_term, src_term)

        for tmp in tmps:
            self.kill(tmp)
        if src_term == Term.get("tmp"):
            self.kill(src_term)

    def _eval_sub_terms(self, term):
        counter = [0]
        return self._eval_sub_terms_recursive(term, counter)

    def _eval_sub_terms_recursive(self, term, counter):
        subterms = []
        tmps = []
        for subterm in term.sub_terms:
            if subterm.sub_terms:
                subterm, tmps2 = \
                    self._eval_sub_terms_recursive(subterm, counter)
                tmp = Term.get("tmp" + str(counter[0]))
                counter[0] += 1
                tmps.append(tmp)
                self._handle_simple_assignment(tmp, subterm)
                subterm = tmp
                for tmp in tmps2:
                    self.kill(tmp)
            subterms.append(subterm)
        return Term.get(term.name, *subterms), tmps

    def _handle_simple_assignment(self, dst, src):
        # if dst.is_deref:
        #     dst = self.simplify_term(dst)
        # src = self.simplify_term(src)

        # print "handling simple", dst, "<-", src

        # print "before"
        # print self
        # print "----------------"

        self.kill(dst)
        self.add_eq(dst, src)

        # print "after"
        # print self
        # print "----------------"

        # if src.is_deref:
        #     self.add_eq(
        #         src, Term.get("deref_%s" % hex(self._instr.addr), src.addr))
        # if dst.name in ["cmp1", "cmp2"]:
        #     self.add_eq(dst, Term.get("_".join([
        #         dst.name, hex(self._instr.addr), str(self.counter)])))

    def kill(self, term):
        if term.is_deref:
            addr = term.addr
            self.clauses = {c.rename(term.name, "d_tmp") for c in self}
            term = term.rename(term.name, "d_tmp")
            self.add_clause(Clause.get({
                Literal.get(Atom.get(VAR.deref(), VAR.d_tmp())),
                Literal.get(Atom.get(VAR, addr))}))

        self.kill_name(term.name)

    def rename(self, old_name, new_name):
        self.clauses = {c.rename(old_name, new_name) for c in self}

    def is_equivalent(self, state):
        solver = Solver()
        b1, b2 = FreshBool(), FreshBool()
        solver.add(b1 == self.z3_expr)
        solver.add(b2 == state.z3_expr)
        solver.add(Not(And(Implies(b1, b2), Implies(b2, b1))))

        # print "comparing"
        # print self
        # print "-------"
        # print state
        # if solver.check() != unsat:
        #     m = solver.model()
        #     print m
        #     raw_input("press any key to continue")
        #     return False
        # return True
        return solver.check() == unsat

    def add_consequences(self):
        ConsequenceFinder(
            self, name_to_kill=None, max_clause_size=self.MAX_CLAUSE_SIZE,
            max_clause_rank=self.MAX_CLAUSE_RANK).run()

        # prev_clauses = set()
        # while prev_clauses != self.clauses:
        #     prev_clauses = self.clauses.copy()
        #     self._add_conseq(self.names)

    def _add_conseq(self, names_to_kill):
        for name in names_to_kill:
            state_copy = self.copy()
            ConsequenceFinder(
                state_copy, name, max_clause_size=self.MAX_CLAUSE_SIZE,
                max_clause_rank=self.MAX_CLAUSE_RANK).run()
            self.clauses |= state_copy.clauses

    def remove_noninvariant_clauses(self, state):
        solver = state.get_solver()
        to_remove = []
        for c in self:
            solver.push()
            solver.add(c.z3_not_expr)
            res = solver.check()
            solver.pop()
            if res != unsat:
                to_remove.append(c)

        self.remove_clauses(to_remove)

    def kill_name(self, name):
        # print "\nkilling", term
        # print "\n", self, "\n"
        ConsequenceFinder(self, name, max_clause_size=self.MAX_CLAUSE_SIZE,
                          max_clause_rank=self.MAX_CLAUSE_RANK).run()
        # print "\nafter", self, "\n"
        # self.strengthen_clauses()
        to_kill = [c for c in self.clauses if name in c.names]

        self.remove_clauses(to_kill)
        self.compactify()

    def compactify(self):
        self.remove_subsumed_clauses()
        # self.strengthen_clauses()
        # self.remove_subsumed_clauses()
        # self.remove_derived_clauses()

    def remove_derived_clauses(self):
        clauses = sorted(self, key=lambda x: (len(x), x.rank, id(x)))
        solver = Solver()
        for c in clauses:
            if c.must_keep:
                solver.add(c.z3_expr)
                continue
            solver.push()
            solver.add(*[(~l).z3_expr for l in c])
            if solver.check() != unsat:
                solver.pop()
                solver.add(c.z3_expr)
            else:
                solver.pop()
                self.clauses.remove(c)

    def strengthen_clauses(self):
        lits = set()
        for c in self:
            lits |= c.literals
        lit_not_expr = {l: Not(l.z3_expr) for l in lits}

        solver = self.get_solver()
        result = {frozenset(): sat}
        to_add = set()

        for c in self:
            worklist = set(c)
            needed = set()
            while worklist:
                l = worklist.pop()
                to_check = frozenset(needed | worklist)
                res = result.get(to_check, None)
                if res is None:
                    solver.push()
                    solver.add(*[lit_not_expr[x] for x in to_check])
                    res = solver.check()
                    solver.pop()
                    result[to_check] = res
                if res != unsat:
                    needed.add(l)
            if needed != c.literals:
                to_add.add(Clause.get(needed))

        self.clauses |= to_add
        self.remove_subsumed_clauses()

    def __iter__(self):
        for c in self.clauses:
            yield c

    def __eq__(self, other):
        return (isinstance(other, AbstractState) and
                self.clauses == other.clauses)

    def __ne__(self, other):
        return self.clauses != other.clauses

    def get_solver(self):
        solver = Solver()
        for c in self:
            solver.add(c.z3_expr)
        return solver

    @property
    def z3_expr(self):
        return And(*[c.z3_expr for c in self])

    @property
    def counter(self):
        AbstractState._counter += 1
        return AbstractState._counter

    def __and__(self, other):
        return AbstractState(self.clauses & other.clauses)

    def __sub__(self, other):
        return AbstractState(self.clauses - other.clauses)

    def __repr__(self):
        if not self:
            return "Empty"
        return "\n".join(map(repr, sorted(self, key=lambda x: len(x))))

    def prime(self):
        return AbstractState({c.prime() for c in self.clauses})

    def remove_big_clauses(self):
        self.remove_clauses(
            {c for c in self
             if len(c) > self.MAX_CLAUSE_SIZE
             or c.rank > self.MAX_CLAUSE_RANK})

    @property
    def names(self):
        names = set()
        for c in self:
            names |= c.names
        return names

    @property
    def atomic_names(self):
        atomic_names = set()
        for c in self:
            atomic_names |= c.atomic_names
        return atomic_names

    @staticmethod
    def merge(*states):
        to_merge = list(states)

        while len(to_merge) > 1:
            state1 = to_merge.pop()
            state2 = to_merge.pop()
            to_merge.append(AbstractState.merge_two_states(state1, state2))

        merged = to_merge[0]

        return merged

    @staticmethod
    def merge_two_states(state1, state2):
        # state1.compactify()
        # state2.compactify()
        if AbstractState.MAX_CLAUSE_SIZE != 2e2000:
            state1.add_consequences()
            state2.add_consequences()

        merged = state1 & state2
        s1_leftovers = state1 - merged
        s2_leftovers = state2 - merged

        for c1, c2 in product(s1_leftovers, s2_leftovers):
            merged.add_clause(c1 | c2)

        merged.remove_big_clauses()
        merged.compactify()

        return merged
