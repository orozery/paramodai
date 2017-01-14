from build_lists.test import test_build_lists
from cve_2014_7841.test import test_cve_2014_7841
from find_last.test import test_find_last
from resource_manager.test import test_resource_manager
from paramodai.test_runner import run_test
import time
import os

if __name__ == "__main__":
    t = time.time()

    curr_path = os.path.dirname(__file__)
    if not curr_path:
        curr_path = "."

    i = 0

    os.chdir(os.sep.join([curr_path, "find_last"]))
    print "Running find_last 2 1"
    i += run_test(test_find_last, ["", 2, 1])
    print "Running find_last 2 2"
    i += run_test(test_find_last, ["", 2, 2])
    print "Running find_last 2 3"
    i += run_test(test_find_last, ["", 2, 3])
    os.chdir(os.sep.join(["..", "resource_manager"]))
    print "Running resource_manager 2 2"
    i += run_test(test_resource_manager, ["", 2, 2])
    os.chdir(os.sep.join(["..", "cve_2014_7841"]))
    print "Running cve_2014_7841 2 -1"
    i += run_test(test_cve_2014_7841, ["", 2, -1])
    os.chdir(os.sep.join(["..", "build_lists"]))
    print "Running build_lists -1 -1"
    i += run_test(test_build_lists, ["", -1, -1])
    print "Total time:", time.time() - t, "seconds"
    print "%d/6 tests succeeded" % i
