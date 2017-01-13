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

import operator
from paramodai.instruction import RETURN_ADDR


class BasicBlock(object):

    __slots__ = ("addr", "cfg", "succs", "preds",
                 "instrs", "_successors", "backgoing_addrs")

    _addr_cache = {}

    def __init__(self, addr, cfg):
        self.addr = addr
        self.cfg = cfg

        self.instrs = []
        if addr != RETURN_ADDR:
            while True:
                instr = self.cfg.executable.get_instr(addr)
                self.instrs.append(instr)
                successors = instr.successors
                if len(successors) != 1:
                    break
                addr, _, _ = successors[0]
                if addr in cfg.bb_entries:
                    break

            self._successors = instr.successors
        else:
            self._successors = []

        self.succs = set([x[0] for x in self._successors])
        self.preds = set()
        self.backgoing_addrs = set()

    @staticmethod
    def get(addr, cfg):
        key = (addr, cfg.entry_addr)
        value = BasicBlock._addr_cache.get(key, None)
        if value is None:
            value = BasicBlock(addr, cfg)
            BasicBlock._addr_cache[key] = value
        return value

    def __iter__(self):
        for instr in self.instrs:
            yield instr

    @property
    def succ_edges(self):
        for addr, assertions, assignments in self._successors:
            is_backward = addr in self.backgoing_addrs
            yield self.cfg[addr], assertions, assignments, is_backward

    @property
    def is_dummy(self):
        return self.addr == RETURN_ADDR

    @property
    def succ_edge_count(self):
        return len(self._successors)

    @property
    def next(self):
        return self.cfg[self.instrs[-1].next_instr_addr]

    @property
    def is_call(self):
        return self.instrs[-1].is_call

    @property
    def is_ret(self):
        return self.instrs[-1].is_ret

    @property
    def backward_reachable_bbs(self):
        worklist = {self}
        seen = set()

        while worklist:
            bb = worklist.pop()
            pred_bbs = {self.cfg[x] for x in bb.preds}
            pred_bbs -= seen
            worklist |= pred_bbs
            seen |= pred_bbs

        return seen

    @property
    def forward_reachable_bbs(self):
        worklist = {self}
        seen = set()

        while worklist:
            bb = worklist.pop()
            succ_bbs = {self.cfg[x] for x in bb.succs}
            succ_bbs -= seen
            worklist |= succ_bbs
            seen |= succ_bbs

        return seen

    @property
    def loop_bbs(self):
        return self.forward_reachable_bbs & self.backward_reachable_bbs

    def __cmp__(self, other):
        return cmp((self.addr, self.cfg.entry_addr),
                   (other.addr, other.cfg.entry_addr))

    def __repr__(self):
        return "BB: " + hex(self.addr)


class CFG(object):

    __slots__ = "entry_addr", "executable", "bb_entries", "basic_blocks"

    _cfg_cache = {}

    def __init__(self, entry_addr, executable):
        self.executable = executable
        self.entry_addr = entry_addr
        self.basic_blocks = {}

        self.bb_entries = self._get_bb_entries()
        self._build_cfg()
        self._mark_backward_edges()

    @property
    def entry_bb(self):
        return self[self.entry_addr]

    def __getitem__(self, addr):
        value = self.basic_blocks.get(addr, None)
        if value is None:
            value = BasicBlock(addr, self)
            self.basic_blocks[addr] = value
        return value

    @staticmethod
    def get(entry_addr, executable):
        key = (entry_addr, executable)
        value = CFG._cfg_cache.get(key, None)
        if value is None:
            value = CFG(entry_addr, executable)
            CFG._cfg_cache[key] = value
        return value

    def _get_bb_entries(self):
        worklist = {self.entry_addr}
        seen = {self.entry_addr}
        while worklist:
            addr = worklist.pop()
            if addr == RETURN_ADDR:
                continue
            while True:
                instr = self.executable.get_instr(addr)
                successors = instr.successors
                if (len(successors) != 1 or instr.is_call or
                        instr.is_jmp or instr.is_ret):
                    break
                addr, _, _ = successors[0]
            new_successors = set([x[0] for x in successors]) - seen
            worklist |= new_successors
            seen |= new_successors

        return seen

    def _build_cfg(self):
        worklist = {self.entry_addr}
        seen = {self.entry_addr}
        while worklist:
            addr = worklist.pop()
            succs = self[addr].succs
            for succ_addr in succs:
                self[succ_addr].preds.add(addr)
            worklist |= succs - seen
            seen |= succs

    def _mark_backward_edges(self):
        all_blocks = set(self.basic_blocks.values())
        dom = {x: all_blocks.copy() for x in all_blocks}
        dom[self.entry_bb] = {self.entry_bb}
        worklist = {self[x] for x in self.entry_bb.succs}
        while worklist:
            bb = worklist.pop()
            if bb == self.entry_bb:
                continue
            new_dom = {bb} | reduce(operator.__and__,
                                    [dom[self[x]] for x in bb.preds])
            if new_dom != dom[bb]:
                dom[bb] = new_dom
                worklist |= {self[x] for x in bb.succs}

        for bb in all_blocks:
            for succ_addr in bb.succs:
                if self[succ_addr] in dom[bb]:
                    bb.backgoing_addrs.add(succ_addr)

    def __repr__(self):
        return "CFG: " + hex(self.entry_addr)
