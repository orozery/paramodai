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
from paramodai.x86 import ESP, DWORD
from paramodai.test_runner import run_test
from z3 import unsat
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
    AbstractState.CONNECTION_ANALYSIS = True
    a = ForwardAnalyzer("build_lists")

    # Add dummy variables that won't be killed so that the malloc transformer
    # would add x != y
    a.assign(Term.get("stk_8"), Term.get("stk_c"), True)

    a.set_func_transformer("allocate_list_item", malloc_transformer)
    a.set_func_transformer("random_selector", random_selector_transformer)
    a.run_from_func("build_lists")

    ret_state = a.get_state(RETURN_ADDR)
    solver = ret_state.get_solver()

    # verify that x (stk_-c) != y (stk_-10) (x not connected to y)
    solver.add(Term.get("stk_-c").z3_expr == Term.get("stk_-10").z3_expr)
    if solver.check() != unsat:
        raise Exception("Proof failed!")


if __name__ == "__main__":
    run_test(test_build_lists, sys.argv)
