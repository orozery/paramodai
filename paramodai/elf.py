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

from executable import Executable, ExecutableParsingError, Section
from elftools.elf.elffile import ELFFile


class ELFExecutable(Executable):

    def _parse_header(self):
        header = file(self.filename, "rb").read(4)

        if not header.startswith("\x7fELF"):
            raise ExecutableParsingError()

        elf = ELFFile(file(self.filename, "rb"))
        if elf.get_machine_arch() == "x86":
            from paramodai.x86 import X86Instruction
            self.elf = elf
            return X86Instruction
        elif elf.get_machine_arch() == "x64":
            print "x64 is not yet supported!"
            raise ExecutableParsingError()
        else:
            print "Unknown ELF machine architecture!"
            raise ExecutableParsingError()

    def _parse_sections(self):
        section = self.elf.get_section_by_name(".text")
        self.add_code_section(section.data(), section.header["sh_addr"])

        section = self.elf.get_section_by_name(".data")
        if section:
            self.add_data_section(section.data(), section.header["sh_addr"])

        section = self.elf.get_section_by_name(".rodata")
        if section:
            self.add_data_section(section.data(), section.header["sh_addr"])

        section = self.elf.get_section_by_name(".bss")
        if section:
            self.add_data_section("\x00"*section.header["sh_size"],
                                  section.header["sh_addr"])

        plt_section = self.elf.get_section_by_name(".plt")
        relplt_section = None
        dynsym = None
        if plt_section is not None:
            plt_section = Section(plt_section.data(),
                                  plt_section.header["sh_addr"])
            relplt_section = self.elf.get_section_by_name(".rel.plt")
            dynsym = self.elf.get_section_by_name(".dynsym")

        for sym in self.elf.get_section_by_name(".symtab").iter_symbols():
            self.symbols[sym["st_value"]] = self.symbols.get(sym["st_value"],
                                                             sym.name)

        if plt_section is None:
            return
        for rel in relplt_section.iter_relocations():
            for i in xrange(plt_section.start_addr+2, plt_section.end_addr-4):
                if plt_section[i] == rel['r_offset']:
                    self.symbols[i-2] = \
                        dynsym.get_symbol(rel['r_info_sym']).name
                    break
