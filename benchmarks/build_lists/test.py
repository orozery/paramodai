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

from paramodai.forward_analysis import ForwardAnalyzer
from paramodai.instruction import RETURN_ADDR
from paramodai.term import Term
from paramodai.state import AbstractState
from paramodai.clause import Clause
from paramodai.literal import Literal
from paramodai.atom import Atom
from paramodai.x86 import ESP, DWORD
from paramodai.test_runner import run_test
from z3 import unsat
from itertools import combinations, permutations
import sys


def malloc_transformer(state, bb):
    state.kill_name("EAX")
    for x in state.atomic_names:
        state.add_eq(Term.get("EAX"), Term.get(x), True)
    state.handle_assignment(ESP, ESP + DWORD)


def random_selector_transformer(state, bb):
    state.kill_name("EAX")
    state.handle_assignment(ESP, ESP + DWORD)


def test_build_lists():

    def _handle_simple_assignment(self, dst, src):
        if dst.is_deref:

            # self.add_consequences()
            # to_remove = []
            # for c in self.clauses.copy():
            #     for l in c:
            #         if not l.sign:
            #             to_remove.append(c)
            #             break
            # self.remove_clauses(to_remove)

            # begin transformer v->f := 0
            self.add_eq(dst.addr, Term.get(0), True)

            var_names = self.atomic_names - {0}
            terms = {}
            old_terms = {}
            for name in var_names:
                terms[name] = Term.get(name)
                old_name = "OLD_" + name
                old_terms[name] = Term.get(old_name)
                self.rename(name, old_name)
            terms[0] = Term.get(0)
            old_terms[0] = Term.get(0)
            v = dst.addr.name

            for u, w in combinations(var_names | {0}, 2):
                self.add_clause(Clause.get({
                    Literal.get(Atom.get(terms[u], terms[w]), True),
                    Literal.get(Atom.get(old_terms[u], old_terms[w]))
                }))

            for u, w in permutations(var_names, 2):
                self.add_clause(Clause.get({
                    Literal.get(Atom.get(old_terms[u], old_terms[w]), True),
                    Literal.get(Atom.get(old_terms[u], old_terms[v])),
                    Literal.get(Atom.get(terms[u], terms[w]))
                }))

            for u in var_names - {v}:
                self.add_clause(Clause.get({
                    Literal.get(Atom.get(terms[u], Term.get(0))),
                    Literal.get(Atom.get(old_terms[u], Term.get(0)), True)
                }))

            for u, w in permutations(var_names, 2):
                self.add_clause(Clause.get({
                    Literal.get(Atom.get(old_terms[u], old_terms[w]), True),
                    Literal.get(Atom.get(old_terms[u], old_terms[v]), True),
                    Literal.get(Atom.get(terms[u], terms[v])),
                    Literal.get(Atom.get(terms[w], terms[v])),
                    Literal.get(Atom.get(terms[u], terms[w]))
                }))

            for name in sorted(var_names, key=lambda x: repr(x)):
                self.kill_name("OLD_" + name)

            # end transformer v->f := 0

            state = self.copy()
            state.add_eq(src, Term.get(0), True)
            self.add_eq(src, Term.get(0))

            for name in var_names:
                state.rename(name, "OLD_" + name)

            for u, w in combinations(var_names | {0}, 2):
                state.add_clause(Clause.get({
                    Literal.get(Atom.get(terms[u], terms[w])),
                    Literal.get(Atom.get(old_terms[u], old_terms[w]), True)
                }))

            for u, w in permutations(var_names | {0}, 2):
                state.add_clause(Clause.get({
                    Literal.get(Atom.get(old_terms[u], old_terms[w])),
                    Literal.get(Atom.get(old_terms[u], old_terms[v])),
                    Literal.get(Atom.get(old_terms[u], old_terms[src.name])),
                    Literal.get(Atom.get(terms[u], terms[w]), True)
                }))

            for name in sorted(var_names, key=lambda x: repr(x)):
                state.kill_name("OLD_" + name)

            state.add_eq(dst.addr, src)

            self.clauses = AbstractState.merge_two_states(
                self, state).clauses
        else:
            self.kill(dst)
            if src.is_atomic:
                self.add_eq(src, dst)
            elif src.is_deref:
                self.add_clause(Clause.get({
                    Literal.get(Atom.get(src.addr, dst)),
                    Literal.get(Atom.get(dst, Term.get(0)))
                }))
                self.add_eq(src.addr, Term.get(0), True)

    AbstractState._handle_simple_assignment = _handle_simple_assignment
    a = ForwardAnalyzer("build_lists")
    a.assign(Term.get("stk_8"), Term.get("stk_c"), True)
    a.set_func_transformer("allocate_list_item", malloc_transformer)
    a.set_func_transformer("random_selector", random_selector_transformer)
    a.run_from_func("build_lists")

    ret_state = a[a.cfg[RETURN_ADDR]]
    solver = ret_state.get_solver()
    solver.add(Term.get("stk_-c").z3_expr == Term.get("stk_-10").z3_expr)
    if solver.check() != unsat:
        raise Exception("Proof failed!")

if __name__ == "__main__":
    run_test(test_build_lists, sys.argv)
