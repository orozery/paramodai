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
import struct


class ExecutableParsingError(Exception):
    pass


class Section(object):

    def __init__(self, data, start_addr):
        self.data = data
        self.start_addr = start_addr
        self.end_addr = start_addr + len(data)

    def __contains__(self, addr):
        return self.start_addr <= addr < self.end_addr

    def __getitem__(self, addr):
        return struct.unpack("<I", self.get_data(addr, 4))[0]

    def get_data(self, addr, count):
        offset = addr-self.start_addr
        return self.data[offset:offset+count]


class CodeSection(Section):

    def __init__(self, data, start_addr, parser, executable):
        Section.__init__(self, data, start_addr)
        self.parser = parser
        self.executable = executable

        self.instructions = {}
        self.prev_instr_addr = {}

    def get_instr(self, addr):
        instr = self.instructions.get(addr, None)
        if instr is None:
            prev_instr = self.prev_instr_addr.pop(addr, None)
            data = self.get_data(addr, 16)
            instr = self.parser(addr, data, prev_instr, self.executable)
            self.instructions[addr] = instr
            self.prev_instr_addr[addr+instr.length] = instr

        return instr


class Executable(object):

    def __init__(self, filename):
        self.filename = filename
        self.symbols = {}
        self.sections = []
        self.code_section = None

        self.parser = self._parse_header()
        self._parse_sections()

        self.symbol_addr = {}
        for addr, sym_name in self.symbols.iteritems():
            self.symbol_addr[sym_name] = addr

    def _parse_header(self):
        raise NotImplementedError()

    def _parse_sections(self):
        raise NotImplementedError()

    def get_cfg(self, addr):
        return CFG.get(addr, self)

    def add_code_section(self, data, addr):
        self.code_section = CodeSection(data, addr, self.parser, self)
        self.sections.append(self.code_section)

    def add_data_section(self, data, addr):
        self.sections.append(Section(data, addr))

    def get_instr(self, addr):
        return self.code_section.get_instr(addr)

    def __getitem__(self, addr):
        for section in self.sections:
            if addr in section:
                return section[addr]

    def __contains__(self, addr):
        for section in self.sections:
            if addr in section:
                return True
        return False

    @staticmethod
    def parse(filename):
        from paramodai.pe import PEExecutable
        from paramodai.elf import ELFExecutable
        containers = [PEExecutable, ELFExecutable]

        executable = None
        for container in containers:
            try:
                executable = container(filename)
            except ExecutableParsingError:
                continue
            break

        if not executable:
            print "Cannot parse file:", filename
            raise ExecutableParsingError()

        return executable
