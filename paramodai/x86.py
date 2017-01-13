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

from paramodai.term import Term, ZERO, ONE
from paramodai.instruction import Instruction, RETURN_ADDR
import distorm3


class X86Instruction(Instruction):

    __slots__ = ("addr", "length", "mnemonic", "operands", "assignments",
                 "successors", "prev_instr")

    REG_NAMES = {"EAX", "EBX", "ECX", "EDX", "EBP", "ESI", "EDI", "ESP"}
    REGS = {Term.get(x) for x in REG_NAMES}
    STACK_REG = Term.get("ESP")

    def __init__(self, addr, data, prev_instr=None, executable=None):
        Instruction.__init__(self)
        instrs = distorm3.Decode(addr, data, distorm3.Decode32Bits)
        _, length, instr_text, _ = instrs[0]
        self.addr = addr
        self.length = length
        self.prev_instr = prev_instr

        (self.mnemonic,
         self.operands) = self.parse_mnemonic_and_operands(instr_text)

        self.assignments = self.parse_assignments(
            self.addr, self.length, self.mnemonic, self.operands)

        self.successors = self.parse_successors(
            self.addr, self.length, self.mnemonic, self.operands,
            prev_instr, executable)

    def __repr__(self):
        s = "%08x: %s" % (self.addr, self.mnemonic)
        if self.operands:
            s += " " + ", ".join(map(repr, self.operands))
        return s

    @property
    def is_call(self):
        return self.mnemonic == "CALL"

    @property
    def is_jmp(self):
        return self.mnemonic.startswith("J")

    @property
    def is_ret(self):
        return self.mnemonic in ["RET", "RETN"]

    @property
    def target(self):
        return self.operands[0]

    @property
    def next_instr_addr(self):
        return self.addr + self.length

    @staticmethod
    def parse_mnemonic_and_operands(instr_text):
        mnemonic_end_pos = instr_text.find(" ")
        if mnemonic_end_pos == -1:
            return instr_text, []

        if instr_text.startswith("REP") or instr_text.startswith("LOCK"):
            mnemonic_end_pos = instr_text.find(" ", mnemonic_end_pos+1)
        mnemonic = instr_text[:mnemonic_end_pos]
        operands = map(X86Instruction.parse_operand,
                       instr_text[mnemonic_end_pos+1:].split(", "))
        return mnemonic, operands

    @staticmethod
    def parse_assignments(addr, length, mnemonic, operands):
        if mnemonic in ["MOV", "MOVZX", "MOVSX"]:
            return [(operands[0], operands[1])]

        elif mnemonic == "LEA":
            return [(operands[0], operands[1].sub_terms[0])]

        elif mnemonic == "PUSH":
            return [(ESP, ESP - DWORD),
                    (ESP.deref(), operands[0])]

        elif mnemonic == "POP":
            return [(operands[0], ESP.deref()),
                    (ESP, ESP + DWORD)]

        elif mnemonic == "LEAVE":
            return [(ESP, EBP),
                    (EBP, ESP.deref()),
                    (ESP, ESP + DWORD)]

        elif mnemonic == "ADD":
            return [(operands[0], operands[0] + operands[1])]

        elif mnemonic == "INC":
            return [(operands[0], operands[0] + ONE)]

        elif mnemonic == "DEC":
            return [(operands[0], operands[0] - ONE)]

        elif mnemonic == "NEG":
            return [(operands[0], -operands[0])]

        elif mnemonic == "SUB":
            return [(operands[0], operands[0] - operands[1])]

        elif mnemonic in ["NOP", "CDQ", "FLDZ"]:
            return []

        elif mnemonic == "FSTP":
            return [(operands[0], None)]

        elif mnemonic.startswith("J"):
            return []

        elif mnemonic.startswith("SET"):
            return []

        elif mnemonic.startswith("CMOV"):
            return []

        elif mnemonic in ["RET", "RETN"]:
            new_ESP = ESP + DWORD
            if len(operands) > 0:
                new_ESP = new_ESP + operands[0]
            return [(ESP, new_ESP)]

        elif mnemonic == "CALL":
            return [(ESP, ESP - DWORD)]

        elif mnemonic == "CMP":
            return [(cmp1, operands[0]),
                    (cmp2, operands[1])]

        elif mnemonic.startswith("REP"):
            if mnemonic.startswith("REP "):
                return [(cmp1, ECX),
                        (cmp2, ZERO)]
            else:
                if " CMPS" in mnemonic:
                    return [(cmp1, ESI.deref()),
                            (cmp2, EDI.deref())]
                elif " SCAS" in mnemonic:
                    return [(cmp1, EDI.deref()),
                            (cmp2, EAX)]
                else:
                    print "Unhandled mnemonic", mnemonic
                    raise NotImplementedError()

        elif mnemonic.startswith("REPE CMP"):
            return [(cmp1, ECX),
                    (cmp2, ZERO)]

        elif mnemonic == "TEST":
            if operands[0] == operands[1]:
                return [(cmp1, operands[0]),
                        (cmp2, ZERO)]

        elif mnemonic == "XOR":
            if operands[0] == operands[1]:
                return [(operands[0], ZERO)]
            else:
                return [(operands[0], None)]

        elif mnemonic in ["OR", "ADC", "SBB", "AND", "ROL", "ROR", "RCL",
                          "RCR", "SAR", "SHL", "SAL", "SHR", "NOT", "BSWAP"]:
            return [(operands[0], None)]

        elif mnemonic in ["IMUL", "MUL"]:
            if len(operands) == 1:
                return [(EDX, None),
                        (EAX, None)]
            else:
                return [(operands[0], None)]

        elif mnemonic in ["DIV"]:
            return [(EDX, None),
                    (EAX, None)]

        elif mnemonic == "XCHG":
            return [(Term.get("tmp_xchg"), operands[0]),
                    (operands[0], operands[1]),
                    (operands[1], Term.get("tmp_xchg")),
                    (Term.get("tmp_xchg"), None)]

        else:
            print "Unhandled mnemonic '%s' at %s" % (mnemonic, hex(addr))
            raise NotImplementedError()

        return []

    @staticmethod
    def _parse_condition(mnemonic_postfix):
        if mnemonic_postfix == "Z":
            return "eq", "ne"
        if mnemonic_postfix == "NZ":
            return "ne", "eq"
        if mnemonic_postfix == "S":
            return "lt", "ge"
        if mnemonic_postfix == "NS":
            return "ge", "lt"
        if mnemonic_postfix in ["AE", "GE"]:
            return "ge", "lt"
        if mnemonic_postfix in ["A", "G"]:
            return "gt", "le"
        if mnemonic_postfix in ["B", "L"]:
            return "lt", "ge"
        if mnemonic_postfix in ["BE", "LE"]:
            return "le", "gt"
        return None, None

    @staticmethod
    def _parse_switch(addr, target, prev_instr, executable):
        if not target.is_deref:
            return
        addr = target.sub_terms[0]
        if addr.name != "add" or len(addr.sub_terms) != 2:
            return
        sub_terms = list(addr.sub_terms)
        if sub_terms[0].name != "mul":
            sub_terms = sub_terms[::-1]
        if sub_terms[0].name != "mul" or sub_terms[0].sub_terms[0] != DWORD:
            return
        offset = sub_terms[0].sub_terms[1]
        orig_offset = offset
        if not offset.is_reg:
            return
        if not sub_terms[1].is_const:
            return
        table_addr = sub_terms[1].name
        if prev_instr.mnemonic.startswith("MOV"):
            dst, src = prev_instr.assignments[0]
            if dst != offset:
                return
            offset = src
            prev_instr = prev_instr.prev_instr
        if prev_instr.mnemonic != "JA":
            return
        prev_instr = prev_instr.prev_instr
        if (prev_instr.mnemonic != "CMP" or
                prev_instr.operands[0] != offset or
                (not prev_instr.operands[1].is_const)):
            return
        table_size = prev_instr.operands[1].name

        res = []
        for i in xrange(table_size):
            case_addr = executable[table_addr+4*i]
            if case_addr not in executable.code_section:
                return
            cond = ("eq", orig_offset, Term.get(i))
            res.append((case_addr, cond))
        return res

    @staticmethod
    def parse_successors(addr, length, mnemonic, operands,
                         prev_instr=None, executable=None):
        if mnemonic in ["RET", "RETN"]:
            return [(RETURN_ADDR, [], [])]

        target = None
        if mnemonic.startswith("J") or mnemonic.startswith("LOOP"):
            target = operands[0]

        next_instr_addr = addr + length

        if mnemonic == "JMP":
            if target.is_const:
                return [(target.name, [], [])]
            else:
                res = X86Instruction._parse_switch(addr, target,
                                                   prev_instr, executable)
                if res is not None:
                    return res
                print "Unhandled jump to", target
                raise NotImplementedError()

        if mnemonic.startswith("CMOV"):

            true_con, false_con = X86Instruction._parse_condition(mnemonic[4:])
            if true_con is None:
                return [(next_instr_addr, [], [(operands[0], operands[1])]),
                        (next_instr_addr, [], [])]

            return [(next_instr_addr,
                     [(true_con, cmp1, cmp2)],
                     [(operands[0], operands[1])]),
                    (next_instr_addr,
                     [(false_con, cmp1, cmp2)],
                     [])]

        if mnemonic.startswith("SET"):

            true_con, false_con = X86Instruction._parse_condition(mnemonic[3:])
            if true_con is None:
                return [(next_instr_addr, [], [(operands[0], ONE)]),
                        (next_instr_addr, [], [])]

            return [(next_instr_addr,
                     [(true_con, cmp1, cmp2)],
                     [(operands[0], ONE)]),
                    (next_instr_addr,
                     [(false_con, cmp1, cmp2)],
                     [(operands[0], ZERO)])]

        if mnemonic.startswith("REP"):
            if mnemonic.startswith("REPE") or mnemonic.startswith("REPZ"):
                true_con, false_con = "eq", "ne"
            else:
                true_con, false_con = "ne", "eq"

            assignments = [(ECX, ECX - ONE)]
            if mnemonic.endswith("B"):
                width = ONE
            elif mnemonic.endswith("W"):
                width = WORD
            else:
                width = DWORD
            if " INS" in mnemonic:
                assignments.append((EDI.deref(), None))
                assignments.append((EDI, EDI + width))
            elif " MOVS" in mnemonic:
                assignments.append((EDI.deref(), ESI.deref()))
                assignments.append((EDI, EDI + width))
                assignments.append((ESI, ESI + width))
            elif " STOS" in mnemonic:
                assignments.append((EDI.deref(), EAX))
                assignments.append((EDI, EDI + width))
            elif " CMPS" in mnemonic:
                assignments.append((EDI, EDI + width))
                assignments.append((ESI, ESI + width))
            elif " SCAS" in mnemonic:
                assignments.append((EDI, EDI + width))
            else:
                print "Unhandled mnemonic", mnemonic
                raise NotImplementedError()

            return [(addr, [(true_con, cmp1, cmp2)], assignments),
                    (next_instr_addr, [(false_con, cmp1, cmp2)], [])]

        if mnemonic.startswith("LOOP"):
            print "Unhandled LOOP instruction:", operands
            raise NotImplementedError()
            # TODO
            # if target.is_const:
            #     return [(next_instr_addr, [], []), (target.name, [], [])]
            # else:
            #     return [(next_instr_addr, [], [])]

        if mnemonic.startswith("J"):

            true_con, false_con = X86Instruction._parse_condition(mnemonic[1:])

            if target.is_const:
                if true_con is None:
                    return [(next_instr_addr, [], []),
                            (target.name, [], [])]
                return [(next_instr_addr, [(false_con, cmp1, cmp2)], []),
                        (target.name, [(true_con, cmp1, cmp2)], [])]
            else:
                print "Unhandled jmp to", target
                raise NotImplementedError()

        return [(next_instr_addr, [], [])]

    @staticmethod
    def parse_operand(operand):
        parse_operand = X86Instruction.parse_operand

        if operand.startswith("["):
            assert operand.endswith("]")
            return parse_operand(operand[1:-1]).deref()
        if operand.startswith("QWORD ["):
            # TODO
            assert operand.endswith("]")
            return parse_operand(operand[7:-1]).deref()
        if operand.startswith("DWORD ["):
            # TODO
            assert operand.endswith("]")
            return parse_operand(operand[7:-1]).deref()
        if operand.startswith("WORD ["):
            # TODO
            assert operand.endswith("]")
            return parse_operand(operand[6:-1]).deref()
        if operand.startswith("BYTE ["):
            # TODO
            assert operand.endswith("]")
            return parse_operand(operand[6:-1]).deref()
        add_pos = operand.rfind("+")
        sub_pos = operand.rfind("-")
        if add_pos > sub_pos:
            args = [operand[:add_pos], operand[add_pos+1:]]
            return parse_operand(args[0]) + parse_operand(args[1])
        if sub_pos >= 0:
            args = [operand[:sub_pos], operand[sub_pos+1:]]
            if not args[0]:
                return -parse_operand(args[1])
            return parse_operand(args[0]) - parse_operand(args[1])
        mul_pos = operand.find("*")
        if mul_pos >= 0:
            args = [operand[:mul_pos], operand[mul_pos+1:]]
            return parse_operand(args[0]) * parse_operand(args[1])
        if operand.startswith("0x"):
            return Term.get(int(operand[2:], 16))
        if operand.isdigit():
            return Term.get(int(operand))
        else:
            if len(operand) == 2:
                operand = "E" + operand[0] + "X"
            return Term.get(operand)


EAX = Term.get("EAX")
ECX = Term.get("ECX")
EDX = Term.get("EDX")
ESI = Term.get("ESI")
EDI = Term.get("EDI")
ESP = Term.get("ESP")
EBP = Term.get("EBP")

cmp1 = Term.get("cmp1")
cmp2 = Term.get("cmp2")

WORD = Term.get(2)
DWORD = Term.get(4)
