from paramodai.forward_analysis import ForwardAnalyzer
from paramodai.term import Term
from paramodai.test_runner import run_test
from z3 import unsat
import sys


def test_cve_2014_7841():
    a = ForwardAnalyzer("cve_2014_7841")

    # state that the global struct addresses are not NULL
    a.assign(Term.get(a.executable.symbol_addr["sctp_af_v4_specific"]),
             Term.get(0), True)
    a.assign(Term.get(a.executable.symbol_addr["sctp_af_v6_specific"]),
             Term.get(0), True)

    a.run_from_func("cve_2014_7841")

    # iterate over all memory loads
    for bb in a.cfg.basic_blocks.itervalues():
        for instr in bb:
            for dst, src in instr.assignments:

                # check that assignment is a memory load (src.is_deref)
                if src.is_deref:

                    # calculate state right before memory load
                    # by advancing the state at the start of the BB
                    state = a[bb].copy()
                    for instr2 in bb:
                        if instr == instr2:
                            break
                        a._apply_instr(state, instr2)

                    solver = state.get_solver()
                    # verify that address cannot be NULL (0)
                    solver.add(src.addr.z3_expr == Term.get(0).z3_expr)
                    if solver.check() != unsat:
                        raise Exception(
                            "Could not prove safe deref on %r" % instr)


if __name__ == "__main__":
    run_test(test_cve_2014_7841, sys.argv)
