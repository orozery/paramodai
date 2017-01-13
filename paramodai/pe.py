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

from executable import Executable, ExecutableParsingError
from dislib import PEFile, IMAGE_FILE_MACHINE_I386, IMAGE_FILE_MACHINE_AMD64


class PEExecutable(Executable):

    def _parse_header(self):
        header = file(self.filename, "rb").read(4)

        if not header.startswith("MZ"):
            raise ExecutableParsingError()

        pe = PEFile(self.filename)
        if pe.MachineType == IMAGE_FILE_MACHINE_I386:
            from paramodai.x86 import X86Instruction
            self.pe = pe
            return X86Instruction
        elif pe.MachineType == IMAGE_FILE_MACHINE_AMD64:
            print "x64 is not yet supported!"
            raise ExecutableParsingError()
        else:
            print "Unknown PE machine type!"
            raise ExecutableParsingError()

    def _parse_sections(self):
        for section in self.pe.Sections:
            name = section.Name
            data = section.Data
            addr = self.pe.ImageBase + section.VA
            if name == ".text":
                self.add_code_section(data, addr)
            elif name in [".rdata", ".data"]:
                self.add_data_section(data, addr)
