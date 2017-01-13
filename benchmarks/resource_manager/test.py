from paramodai.forward_analysis import ForwardAnalyzer
from paramodai.instruction import RETURN_ADDR
from paramodai.term import Term
from paramodai.x86 import ESP, DWORD
from paramodai.test_runner import run_test
from z3 import unsat
import sys


def random_selector_transformer(state, bb):
    state.kill_name("EAX")
    state.handle_assignment(ESP, ESP + DWORD)


def test_resource_manager():
    a = ForwardAnalyzer("resource_manager")
    a.set_func_transformer("random_selector", random_selector_transformer)
    a.assign(Term.get(0), Term.get(1), True)
    a.assign(Term.get(0), Term.get(2), True)
    a.assign(Term.get(1), Term.get(2), True)
    a.run_from_func("resource_manager")
    ret_state = a[a.cfg[RETURN_ADDR]]
    solver = ret_state.get_solver()
    solver.add(Term.get("stk_-14").z3_expr != Term.get(0).z3_expr)
    solver.add(Term.get("stk_-18").z3_expr != Term.get(1).z3_expr)
    if solver.check() != unsat:
        raise Exception("Proof failed!")


if __name__ == "__main__":
    run_test(test_resource_manager, sys.argv)
