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

from paramodai.cfg import CFG


class Context(object):

    __slots__ = "bb", "return_ctx"

    _context_cache = {}

    def __init__(self, bb, return_ctx):
        self.bb = bb
        self.return_ctx = return_ctx

    @staticmethod
    def get(bb, return_ctx=None):
        key = (return_ctx, bb)
        value = Context._context_cache.get(key, None)
        if value is None:
            value = Context(bb, return_ctx)
            Context._context_cache[key] = value
        return value

    @property
    def cfg(self):
        return self.bb.cfg

    @property
    def executable(self):
        return self.cfg.executable

    def change_bb(self, bb):
        return Context.get(bb, self.return_ctx)

    @property
    def next_ctx(self):
        return self.change_bb(self.bb.next)

    def call(self, addr):
        assert self.bb.is_call
        called_bb = CFG.get(addr, self.executable).entry_bb
        return_ctx = self.next_ctx
        return Context.get(called_bb, return_ctx)

    def ret(self):
        assert self.bb.is_ret
        return self.return_ctx

    @property
    def callstack(self):
        if self.return_ctx:
            return self.return_ctx.callstack + (self.bb,)
        else:
            return self.bb,

    def __cmp__(self, other):
        if other is None:
            return 1
        return cmp(self.callstack, other.callstack)

    def __repr__(self):
        return repr([hex(bb.addr) for bb in self.callstack]).replace("'", "")
