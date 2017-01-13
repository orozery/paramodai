from paramodai.forward_analysis import ForwardAnalyzer
from paramodai.instruction import RETURN_ADDR
from paramodai.term import Term
from paramodai.test_runner import run_test
from z3 import unsat
import sys


def test_find_last():
    a = ForwardAnalyzer("find_last")
    a.run_from_func("find_last")
    ret_state = a[a.cfg[RETURN_ADDR]]
    solver = ret_state.get_solver()
    solver.add(Term.get("EAX").z3_expr != Term.get(0).z3_expr)
    solver.add(Term.get("EAX").deref().z3_expr != Term.get("stk_8").z3_expr)
    if solver.check() != unsat:
        raise Exception("Proof failed!")


if __name__ == "__main__":
    run_test(test_find_last, sys.argv)
