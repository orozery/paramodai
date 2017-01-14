from paramodai.forward_analysis import ForwardAnalyzer
from paramodai.instruction import RETURN_ADDR
from paramodai.term import Term
from paramodai.state import AbstractState
from z3 import unsat
import sys
import time


def test_null_rc(argv):
    if len(argv) != 5:
        print "Usage: %s <executable_path> <function_name> " \
              "<k_max_clause> <d_max_rank>\n-1 indicates infinite" % argv[0]
        return

    filename = argv[1]
    func_name = argv[2]
    max_clause = int(argv[3])
    max_rank = int(argv[4])
    if max_clause == -1:
        max_clause = 2e2000
    if max_rank == -1:
        max_rank = 2e2000

    AbstractState.MAX_CLAUSE_SIZE = max_clause
    AbstractState.MAX_CLAUSE_RANK = max_rank

    t = time.time()
    try:
        a = ForwardAnalyzer(filename)
        a.run_from_func(func_name)
        ret_state = a.get_state(RETURN_ADDR)
        solver = ret_state.get_solver()
        solver.add(Term.get("EAX").z3_expr != Term.get(0).z3_expr)
        if solver.check() != unsat:
            raise Exception("Proof failed!")
    except Exception as e:
        print "\n\nTest failed"
        print "Reason:", e
    else:
        print "\n\nTest succeeded!"

    print "Running time:", time.time() - t


if __name__ == "__main__":
    test_null_rc(sys.argv)
