import time
from paramodai.state import AbstractState


def run_test(test_func, argv):
    if len(argv) != 3:
        print "Usage: %s <k_max_clause> <d_max_rank>\n-1 indicates infinite" % argv[0]
        return

    max_clause = int(argv[1])
    max_rank = int(argv[2])
    if max_clause == -1:
        max_clause = 2e2000
    if max_rank == -1:
        max_rank = 2e2000

    AbstractState.MAX_CLAUSE_SIZE = max_clause
    AbstractState.MAX_CLAUSE_RANK = max_rank

    t = time.time()
    try:
        test_func()
    except Exception as e:
        print "\n\nTest failed"
        print "Reason:", e
    else:
        print "\n\nTest succeeded!"

    print "Running time:", time.time() - t
