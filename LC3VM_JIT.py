from __future__ import annotations
from Annotations import *
import numpy as np
import numba
import time, random

opcodeMap = {0b0001: 'ADD', 0b0101: 'AND', 0b0000: 'BR', 0b1100: 'JMP', 0b0100: 'JSR',
             0b0010: 'LD', 0b1010: 'LDI', 0b0110: 'LDR', 0b1110: 'LEA', 0b1001: 'NOT',
             0b1000: 'RTI', 0b0011: 'ST', 0b1011: 'STI', 0b0111: 'STR', 0b1111: 'TRAP'}


@numba.njit
def getBitField(value: np.uint16, start: int, end: int, signed: bool = False) -> np.uint16:
    result = (value >> end) & ((1 << (start - end + 1)) - 1)
    if signed:
        dataWidth = start - end
        signBit = (result << (15 - dataWidth) >> 15)
        if signBit == 1: result |= ((0xFFFF - result) >> (dataWidth + 1)) << (dataWidth + 1)
    return result


class LC3Integer:
    def __init__(self, value: Int):
        self.value = np.uint16(value)

    def getUnsigned(self):
        return self.value

    def getSigned(self):
        return np.int16(self.value)

    def getBitField(self, start: int, end: int, signed=False) -> LC3Integer:
        return LC3Integer(getBitField(self.value, start, end, signed))

    def __getitem__(self, item: slice):
        return self.getBitField(item.start, item.stop, item.step)

    def __str__(self):
        return str(self.value)


Int = Union[int, np.uint16]

spec = [('memory', numba.uint16[:]),
        ('registers', numba.uint16[:]),
        ('PC', numba.uint16),
        ('IR', numba.uint16),
        ('PSR', numba.uint16),
        ('isHalted', numba.boolean)]


@numba.experimental.jitclass(spec)
class LC3VM:
    def __init__(self):
        self.memory = np.array([0 for _ in range(65535)], dtype=np.uint16)
        self.registers = np.array([0 for _ in range(8)], dtype=np.uint16)
        self.PC, self.IR, self.PSR = np.uint16(0x3000), np.uint16(0b0000000000000000), np.uint16(0b0000000000000000)
        self.isHalted = False

    def readMemory(self, loc: Int) -> Int:
        return self.memory[loc]

    def writeMemory(self, loc: Int, data: Int):
        self.memory[loc] = data

    def readRegister(self, regIndex: Int) -> Int:
        return self.registers[regIndex]

    def writeRegister(self, regIndex: Int, data: Int):
        self.registers[regIndex] = data

    def setcc(self):
        value = np.int16(self.readRegister(getBitField(self.IR, 11, 9)))
        self.PSR &= 0b1111111111111000
        if value < 0:
            self.PSR |= 0b0000000000000100
        elif value == 0:
            self.PSR |= 0b0000000000000010
        elif value > 0:
            self.PSR |= 0b0000000000000001

    def fetch(self):
        self.IR = self.readMemory(self.PC)
        self.PC += 1

    def route(self):
        opcode = getBitField(self.IR, 15, 12, False)
        if opcode == 0b0001:
            self.opADD()
        elif opcode == 0b0101:
            self.opAND()
        elif opcode == 0b0000:
            self.opBR()
        elif opcode == 0b1100:
            self.opJMP()
        elif opcode == 0b0100:
            self.opJSR()
        elif opcode == 0b0010:
            self.opLD()
        elif opcode == 0b1111:
            self.isHalted = True

    def opADD(self):
        DR, SR1, immFlag = getBitField(self.IR, 11, 9), getBitField(self.IR, 8, 6), getBitField(self.IR, 5, 5)
        if immFlag == 0:
            SR2 = getBitField(self.IR, 2, 0)
            self.writeRegister(DR, self.readRegister(SR1) + self.readRegister(SR2))
        else:
            imm5 = getBitField(self.IR, 4, 0, True)
            self.writeRegister(DR, self.readRegister(SR1) + imm5)
        self.setcc()

    def opAND(self):
        DR, SR1, immFlag = getBitField(self.IR, 11, 9), getBitField(self.IR, 8, 6), getBitField(self.IR, 5, 5)
        if immFlag == 0:
            SR2 = getBitField(self.IR, 2, 0)
            self.writeRegister(DR, self.readRegister(SR1) & self.readRegister(SR2))
        else:
            imm5 = getBitField(self.IR, 4, 0, True)
            self.writeRegister(DR, self.readRegister(SR1) & imm5)
        self.setcc()

    def opBR(self):
        n, z, p = getBitField(self.IR, 11, 11), getBitField(self.IR, 10, 10), getBitField(self.IR, 9, 9)
        N, Z, P = getBitField(self.PSR, 2, 2), getBitField(self.PSR, 1, 1), getBitField(self.PSR, 0, 0)
        if (n and N) or (z and Z) or (p and P):
            PCoffset9 = np.int16(getBitField(self.IR, 8, 0, True))
            self.PC += PCoffset9

    def opJMP(self):
        BaseR = getBitField(self.IR, 8, 6)
        self.PC = self.readRegister(BaseR)

    def opJSR(self):
        offsetFlag = getBitField(self.IR, 11, 11)
        self.writeRegister(7, self.PC)
        if offsetFlag == 0:
            BaseR = getBitField(self.IR, 8, 6)
            self.PC = self.readRegister(BaseR)
        else:
            PCoffset11 = np.int16(getBitField(self.IR, 10, 0, True))
            self.PC += PCoffset11

    def opLD(self):
        DR, PCoffset9 = getBitField(self.IR, 11, 9), np.int16(getBitField(self.IR, 8, 0))
        self.writeRegister(DR, self.readMemory(self.PC + PCoffset9))
        self.setcc()

    def cycle(self):
        self.fetch()
        self.route()

    def run(self):
        while not self.isHalted: self.cycle()


def speedTest():
    from time import time
    startTime = time()
    processor = LC3VM()
    for offset, inst in enumerate([0x2406, 0x2206, 0x127f, 0x7fe, 0x14bf, 0x7fb, 0xf025, 0xa, 0x7fff]):
        processor.writeMemory(0x3000 + offset, inst)
    processor.run()
    timeCost = time() - startTime
    print(timeCost)
    print(f"Speed:{int(710930 / timeCost / 1000)} kHz")


speedTest()
