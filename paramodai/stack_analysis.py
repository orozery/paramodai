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
from paramodai.term import Term
from paramodai.x86 import ESP


class StackAnalyzer(ForwardAnalyzer):

    def get_startup_state(self):
        return {self.executable.parser.STACK_REG: 0}

    def run_from_addr(self, addr):
        self.init(addr)
        self.run()

    def merge(self, bb, state_list):
        curr_state = self.get(bb, None)
        if curr_state is not None:
            state_list.append(curr_state)
        merged = {}
        for state in state_list:
            for key, value in state.iteritems():
                if merged.get(key) not in {None, value}:
                    raise Exception(
                        "Found stack inconsistency at addr: %x, key: %r!" %
                        (bb.addr, key))
                merged[key] = value
        self[bb] = merged
        return curr_state is None or self[bb] != curr_state

    def get_stack_offset(self, state, op):
        if op.is_atomic:
            return state.get(op)

        if op.name == "add":
            reg, offset = [x.simplify() for x in op.sub_terms]

            if reg.is_const:
                offset, reg = reg, offset
            val = self.get_stack_offset(state, reg)

            if val is not None and offset.is_const:
                return val + offset.name

    def simplify(self, state, op):

        if op.is_deref:
            addr = op.sub_terms[0]
            stack_offset = self.get_stack_offset(state, addr)
            if stack_offset is not None:
                return Term.get("stk_%x" % stack_offset)
        else:
            return Term.get(op.name,
                            *[self.simplify(state, x) for x in op.sub_terms])

        return op

    def _apply_instr(self, state, instr):
        fixed_assignments = []
        for dst_operand, src_operand in instr.assignments:
            fixed_assignments.append((self.simplify(state, dst_operand),
                                      self.simplify(state, src_operand)))

            stack_offset = self.get_stack_offset(state, src_operand)
            if dst_operand.is_atomic:
                if stack_offset is not None:
                    state[dst_operand] = stack_offset
                else:
                    try:
                        state.pop(dst_operand)
                    except KeyError:
                        pass
        instr.assignments = fixed_assignments

        # print "fixed", fixed_assignments

    def _propagate_call(self, state, bb):
        state[ESP] += 4
        return self._propagate_intraprocedural(state, bb)

    def _propagate_intraprocedural(self, state, bb):
        for target, assertions, assignments, is_backward in bb.succ_edges:

            yield target, state.copy()
