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

from paramodai.executable import Executable
from paramodai.cfg import CFG
from paramodai.state import AbstractState
from paramodai.term import Term
from heapq import heappush, heappop


class UndeterminedCallExecption(Exception):
    pass


class BBWorklist(object):

    def __init__(self):
        self.clear()

    def push(self, bb, state):
        if bb not in self._bb_set:
            self._bb_set.add(bb)
            heappush(self._bb_heap, bb)
            self._states[bb] = [state]
        else:
            self._states[bb].append(state)

    def pop(self):
        bb = heappop(self._bb_heap)
        self._bb_set.remove(bb)
        return bb, self._states.pop(bb)

    def clear(self):
        self._bb_heap = []
        self._bb_set = set()
        self._states = {}

    def __len__(self):
        return len(self._bb_set)


class ForwardAnalyzer(dict):

    debug = 0

    def __init__(self, filename):
        super(ForwardAnalyzer, self).__init__(self)
        self.filename = filename
        self.executable = Executable.parse(filename)
        self.func_transformers = {}
        self.startup_assignments = []
        self.visited_funcs = set()

    def init_from_func(self, func_name, start_state=None):
        start_addr = self.executable.symbol_addr[func_name]
        self.init(start_addr, start_state)

    def run_from_func(self, func_name, start_state=None):
        self.init_from_func(func_name, start_state)
        self.run()

    def init(self, start_addr, start_state=None):
        from paramodai.stack_analysis import StackAnalyzer
        if not isinstance(self, StackAnalyzer):
            sa = StackAnalyzer(self.filename)
            sa.run_from_addr(start_addr)
            self.cfg = sa.cfg
        else:
            self.cfg = CFG.get(start_addr, self.executable)
        self.worklist = BBWorklist()
        self.delayed_worklist = BBWorklist()
        if start_state is None:
            start_state = self.get_startup_state()
        self.worklist.push(self.cfg.entry_bb, start_state)

    def run(self):
        while True:
            while self.worklist:

                bb, state_list = self.worklist.pop()

                if self.debug > 0:
                    print bb
                    if self.debug > 2:
                        for state in state_list:
                            print "-------new--------"
                            print state
                        print "--------old-------"
                        print self.get(bb, None)
                        print
                        print

                self._process_item(bb, state_list)

            if not self.delayed_worklist:
                break

            bb, state_list = self.delayed_worklist.pop()
            self._process_delayed_item(bb, state_list)

    def _process_delayed_item(self, bb, state_list):
        old_state = self[bb]
        new_state = AbstractState.merge(*state_list)
        if old_state.is_equivalent(new_state):
            return
        print "======= old_state ==========="
        print old_state

        from z3 import unsat
        s = old_state.get_solver()
        s.add(Term.get("stk_-c").z3_expr != Term.get(0).z3_expr)
        s.add(Term.get("stk_8").z3_expr != Term.get("stk_-c").deref().z3_expr)
        if s.check() != unsat:
            raise Exception("1")

        # from z3 import unsat
        # s = old_state.get_solver()
        # s.add(Term.get("stk_-c").z3_expr != Term.get(0xffffffff).z3_expr)
        # s.add(Term.get("stk_-18").z3_expr != Term.get("add", Term.get("stk_4"), Term.get("stk_-c")).deref().z3_expr)
        # if s.check() != unsat:
        #     raise Exception("1")

        print "======= new_state ==========="
        print new_state

        from z3 import unsat
        s = old_state.get_solver()
        s.add(Term.get("stk_-c").z3_expr != Term.get(0).z3_expr)
        s.add(Term.get("stk_8").z3_expr != Term.get("stk_-c").deref().z3_expr)
        if s.check() != unsat:
            raise Exception("2")

        # s = new_state.get_solver()
        # s.add(Term.get("stk_-c").z3_expr != Term.get(0xffffffff).z3_expr)
        # s.add(Term.get("stk_-18").z3_expr != Term.get("add", Term.get("stk_4"),
        #                                               Term.get(
        #                                                   "stk_-c")).deref().z3_expr)
        # if s.check() != unsat:
        #     raise Exception("2")

        # new_state.compactify()
        # new_state.add_consequences()
        # new_state.clauses = {c for c in new_state.clauses if len(c) <= 3}
        # new_state.remove_noninvariant_clauses(old_state)
        # new_state.compactify()
        new_state = AbstractState.merge_two_states(old_state, new_state)
        print "======= after ==========="
        print new_state

        from z3 import unsat
        s = old_state.get_solver()
        s.add(Term.get("stk_-c").z3_expr != Term.get(0).z3_expr)
        s.add(Term.get("stk_8").z3_expr != Term.get("stk_-c").deref().z3_expr)
        if s.check() != unsat:
            raise Exception("3")

        # s = new_state.get_solver()
        # s.add(Term.get("stk_-c").z3_expr != Term.get(0xffffffff).z3_expr)
        # s.add(Term.get("stk_-18").z3_expr != Term.get("add", Term.get("stk_4"),
        #                                               Term.get(
        #                                                   "stk_-c")).deref().z3_expr)
        # if s.check() != unsat:
        #     raise Exception("3")
        self.pop(bb)
        self.worklist.push(bb, new_state)

    def _process_item(self, bb, state_list):
        if not self.merge(bb, state_list):
            if self.debug:
                print "\n\n\n\nNOTHING NEWWWWWWW\n\n\n\n"
            return

        if self.debug > 0:
            print "\t", len(self[bb])
            if self.debug > 1:
                print "after merge"
                print self[bb]
                raw_input("press any key to continue:")
                print
                print

        if bb.is_dummy:
            return

        for succ_bb, succ_state in \
                self.apply_block(self[bb], bb):
            self.worklist.push(succ_bb, succ_state)

    def get_startup_state(self):
        state = AbstractState()
        # self.assign(self.executable.parser.STACK_REG, STACK)
        # from paramodai.term import VAR
        # self.assign(VAR.deref(), VAR.arg_deref())
        # for reg_name in self.executable.parser.REG_NAMES:
        #     self.assign(Term.get(reg_name), Term.get("!" + reg_name))
        for dst, src, sign in self.startup_assignments:
            state.add_eq(dst, src, sign)
        return state

    def get_state(self, addr):
        return self[self.cfg[addr]]

    # def get_contexts(self, addr):
    #     res = []
    #     for ctx in self:
    #         if ctx and ctx.bb.addr == addr:
    #             res.append(ctx)
    #     return res

    def apply_block(self, state, bb):
        new_state = state.copy()
        for instr in bb:
            self._apply_instr(new_state, instr)

        return self._propagate(new_state, bb)

    def set_func_transformer(self, func_name, transformer):
        func_addr = self.executable.symbol_addr[func_name]
        self.func_transformers[func_addr] = transformer

    def assign(self, dst, src, sign=False):
        self.startup_assignments.append((dst, src, sign))

    def set_global_to_value(self, global_name, value):
        global_addr = self.executable.symbol_addr[global_name]
        global_op = Term.get(global_addr).deref()
        self.startup_assignments.append((global_op, Term.get(value), False))

    def initialize_global(self, global_name, size_in_dwords=1):
        global_addr = self.executable.symbol_addr[global_name]
        for i in xrange(size_in_dwords):
            addr = global_addr+4*i
            global_op = Term.get(addr).deref()
            value = Term.get(self.executable[addr])
            self.startup_assignments.append((global_op, value, False))

    def _apply_instr(self, state, instr):
        # print "@@@@@@@@@@@@@@@@@@@@@@ applying", instr

        # if instr.addr > 0x080484AD:
        #     from z3 import unsat
        #     s = state.get_solver()
        #     s.add(Term.get("stk_-c").z3_expr != Term.get(0).z3_expr)
        #     s.add(
        #         Term.get("stk_8").z3_expr != Term.get("stk_-c").deref().z3_expr)
        #     if s.check() != unsat:
        #         raise Exception("4")

        state._instr = instr
        # print len(state)
        for dst_operand, src_operand in instr.assignments:
            state.handle_assignment(dst_operand, src_operand)
        # print state

        # if instr.addr > 0x080484AD:
        #     from z3 import unsat
        #     s = state.get_solver()
        #     s.add(Term.get("stk_-c").z3_expr != Term.get(0).z3_expr)
        #     s.add(
        #         Term.get("stk_8").z3_expr != Term.get("stk_-c").deref().z3_expr)
        #     if s.check() != unsat:
        #         raise Exception("5")
        # raw_input()

    def _propagate_call(self, state, bb):
        target = bb.instrs[-1].target
        if not target.is_const:
            print "Cannot preform call to", target
            raise UndeterminedCallExecption()
        addr = target.name
        new_state = state.copy()
        transformer = self.func_transformers.get(addr, None)
        if transformer is not None:
            transformer(new_state, bb)
            for x in self._propagate_intraprocedural(new_state, bb):
                yield x
            return

        print "Cannot preform call to", target
        raise UndeterminedCallExecption()

        # if addr in self.executable.code_section:
        #     if addr not in self.visited_funcs:
        #         self.visited_funcs.add(addr)
        #         print "visited", self.executable.symbols[addr]
        #     yield ctx.call(addr), new_state
        # else:
        #     print "Cannot preform call to", target
        #     print "Context:", ctx
        #     raise UndeterminedCallExecption()

    def _propagate_ret(self, state, bb):
        return self._propagate_intraprocedural(state, bb)
        # yield ctx.ret(), state

    def _propagate(self, state, bb):
        if bb.is_call:
            return self._propagate_call(state, bb)
        elif bb.is_ret:
            return self._propagate_ret(state, bb)
        else:
            return self._propagate_intraprocedural(state, bb)

    def _propagate_intraprocedural(self, state, bb):
        new_states = [state] + [state.copy()
                                for i in xrange(bb.succ_edge_count-1)]

        for target, assertions, assignments, is_backward in bb.succ_edges:

            ret_state = new_states.pop()

            if not ret_state.handle_assertions(assertions):
                continue
            for dst, src in assignments:
                ret_state.handle_assignment(dst, src)

            # optimization
            ret_state.kill_name("cmp1")
            ret_state.kill_name("cmp2")

            # if is_backward:
            #     print "BACKWARDDD"
            #     print ret_state
            #     raw_input("press any key")

            if is_backward and False:
                self.delayed_worklist.push(target, ret_state)
            else:
                yield target, ret_state

    def merge(self, bb, state_list):
        curr_state = self.get(bb, None)
        if curr_state is not None:
            state_list.append(curr_state)
        self[bb] = AbstractState.merge(*state_list)
        return curr_state is None or self[bb] != curr_state
