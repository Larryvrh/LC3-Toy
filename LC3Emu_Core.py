from LC3Emu_Util import *
from re import sub, Pattern
from re import compile as reCompile


def compileMatchPatterns():
    patterns = {'0001': '[DR,3][SR1,3](000[SR2,3]|1[imm5,5])',
                '0101': '[DR,3][SR1,3](000[SR2,3]|1[imm5,5])',
                '0000': '[n,1][z,1][p,1][PCoffset9,9]',
                '1100': '000111000000|000[BaseR,3]000000',
                '0100': '1[PCoffset11,11]|000[BaseR,3]000000',
                '0010': '[DR,3][PCoffset9,9]',
                '1010': '[DR,3][PCoffset9,9]',
                '0110': '[DR,3][BaseR,3][offset6,6]',
                '1110': '[DR,3][PCoffset9,9]',
                '1001': '[DR,3][SR,3]111111',
                '1000': '00000000000000',
                '0011': '[SR,3][PCoffset9,9]',
                '1011': '[SR,3][PCoffset9,9]',
                '0111': '[SR,3][BaseR,3][offset,6]',
                '1111': '0000[trapvect8,8]'}
    for opcode, opformat in patterns.items():
        opPattern = sub(r'(\[(\S+?),(\d{1,2})\])', lambda i: f'(?P<{i.group(2)}>\d' + '{' + i.group(3) + '})', opcode + opformat)
        patterns[opcode] = reCompile(opPattern)
    return patterns


instructionPatterns: Dict[Str, Pattern] = compileMatchPatterns()


def SEXT(num: Str) -> Str:
    return fill(num, num[0], 16)


def ZEXT(num: Str) -> Str:
    return fill(num, '0', 16)


def isValidData(num: Int) -> Bool:
    if (num >= 0):
        return num.bit_length() <= 15
    else:
        return (num + 1).bit_length() >= 15


class Memory:

    def __init__(self):
        # Memory data units
        self.units = [0 for _ in range(65535)]

    def read(self, loc: Int) -> Int:
        assert 0 <= loc <= 65535
        return self.units[loc]

    def write(self, loc: Int, data: Int):
        assert 0 <= loc <= 65535
        self.units[loc] = data


class Processor:
    def __init__(self, memory: Memory):
        # General purpose registers
        self.registers = [0 for _ in range(8)]
        # Special registers
        self.PC, self.PSR, self.IR = 0x3000, 0b0000000000000000, 0x0
        # Bind memory
        self.memory = memory
        # Instruction details
        self.instruction = {}
        # Operation map
        self.operationMap = {'0001': self.operationADD, '0010': self.operationLD, '0101': self.operationAND,
                             '0000': self.operationBR, '1100': self.operationJMP, '0100': self.operationJSR,
                             '1010': self.operationLDI, '0110': self.operationLDR, '1110': self.operationLEA,
                             '1001': self.operationNOT, '1111': self.operationTRAP}

    def readRegister(self, regIndex: Int) -> Int:
        assert 0 <= regIndex <= 7
        return self.registers[regIndex]

    def writeRegister(self, regIndex: Int, data: Int):
        assert 0 <= regIndex <= 7
        self.registers[regIndex] = data

    def cycleStageFetch(self):
        self.IR = self.memory.read(self.PC)
        self.PC += 1

    def cycleStageDecode(self):
        instruction = decToBin(self.IR, 16, True)
        opCode = instruction[:4]
        assert opCode in instructionPatterns
        self.instruction = {'OPCODE': opCode}
        self.instruction.update(instructionPatterns[opCode].match(instruction).groupdict())
        self.instruction = {k: v for k, v in self.instruction.items() if v is not None}

    def cycleStageEvaluateAddress(self):
        evaluateKeys = ['PCoffset9', 'PCoffset11', 'offset6']
        for key in evaluateKeys:
            if key in self.instruction:
                self.instruction[key] = binToDec(self.instruction[key])

    def cycleStageFetchOperand(self):
        evaluateKeys = ['SR1', 'SR2', 'SR', 'BaseR']
        for key in evaluateKeys:
            if key in self.instruction:
                self.instruction[key] = self.readRegister(binToDec('0' + self.instruction[key]))
        evaluateKeys = ['DR', 'n', 'z', 'p']
        for key in evaluateKeys:
            if key in self.instruction:
                self.instruction[key] = binToDec('0' + self.instruction[key])
        if ('imm5' in self.instruction):
            self.instruction['imm5'] = binToDec(self.instruction['imm5'])

    def cycleStageExecute(self):
        if (self.instruction['OPCODE'] in self.operationMap):
            self.operationMap[self.instruction['OPCODE']]()

    def cycleStageStore(self):
        instruction = self.instruction
        if (instruction['OPCODE'] == '0011'):
            self.memory.write(self.PC + instruction['PCoffset9'], instruction['SR'])
        elif (instruction['OPCODE'] == '1011'):
            self.memory.write(self.memory.read(self.PC + instruction['PCoffset9']), instruction['SR'])
        elif (instruction['OPCODE'] == '0111'):
            self.memory.write(instruction['BaseR'] + instruction['offset6'], instruction['SR'])

    def operationADD(self):
        instruction = self.instruction
        if ('SR2' in instruction):
            self.writeRegister(instruction['DR'], instruction['SR1'] + instruction['SR2'])
        else:
            self.writeRegister(instruction['DR'], instruction['SR1'] + instruction['imm5'])
        self.setcc()

    def operationLD(self):
        instruction = self.instruction
        self.writeRegister(instruction['DR'], self.memory.read(self.PC + instruction['PCoffset9']))
        self.setcc()

    def operationAND(self):
        instruction = self.instruction
        if ('SR2' in instruction):
            self.writeRegister(instruction['DR'], instruction['SR1'] & instruction['SR2'])
        else:
            self.writeRegister(instruction['DR'], instruction['SR1'] & instruction['imm5'])
        self.setcc()

    def operationBR(self):
        instruction = self.instruction
        pN, pZ, pP = map(int, decToBin(self.PSR, 16, True)[-3:])
        if ((instruction['n'] and pN) or (instruction['z'] and pZ) or (instruction['p'] and pP)):
            self.PC = self.PC + instruction['PCoffset9']

    def operationJMP(self):
        instruction = self.instruction
        self.PC = instruction['BaseR']

    def operationJSR(self):
        instruction = self.instruction
        if ('BaseR' in instruction):
            self.PC = instruction['BaseR']
        else:
            self.PC += instruction['PCoffset11']

    def operationLDI(self):
        instruction = self.instruction
        self.writeRegister(instruction['DR'], self.memory.read(self.memory.read(self.PC + instruction['PCoffset9'])))
        self.setcc()

    def operationLDR(self):
        instruction = self.instruction
        self.writeRegister(instruction['DR'], self.memory.read(instruction['BaseR'] + instruction['offset6']))
        self.setcc()

    def operationLEA(self):
        instruction = self.instruction
        self.writeRegister(instruction['DR'], self.PC + instruction['PCoffset9'])
        self.setcc()

    def operationNOT(self):
        instruction = self.instruction
        self.writeRegister(instruction['DR'], ~instruction['SR'])
        self.setcc()

    def operationRTI(self):
        if (decToBin(self.PSR, 16, True) == '0'):
            self.PC = self.memory.read(self.readRegister(6))
            self.writeRegister(6, self.readRegister(6) + 1)
            self.PSR = self.memory.read(self.readRegister(6))
            self.writeRegister(6, self.readRegister(6) + 1)

    def operationTRAP(self):
        instruction = self.instruction
        self.writeRegister(7, self.PC)
        self.PC = self.memory.read(instruction['trapvect8'])

    def setcc(self):
        assert 'DR' in self.instruction
        if (self.readRegister(self.instruction['DR']) < 0):
            self.PSR = binToDec(decToBin(self.PSR, 16, True)[:-3] + '100')
        elif (self.readRegister(self.instruction['DR']) == 0):
            self.PSR = binToDec(decToBin(self.PSR, 16, True)[:-3] + '010')
        else:
            self.PSR = binToDec(decToBin(self.PSR, 16, True)[:-3] + '001')

    def cycle(self):
        self.cycleStageFetch()
        self.cycleStageDecode()
        self.cycleStageEvaluateAddress()
        self.cycleStageFetchOperand()
        self.cycleStageExecute()
        self.cycleStageStore()

    def run(self):
        while (True):
            self.cycleStageFetch()
            self.cycleStageDecode()
            # print(self.instruction)
            if (self.instruction['OPCODE'] == '1111'):
                break
            self.cycleStageEvaluateAddress()
            self.cycleStageFetchOperand()
            self.cycleStageExecute()
            self.cycleStageStore()


def speedTest():
    from time import time
    startTime = time()
    tempMemory = Memory()
    processor = Processor(tempMemory)
    for offset, inst in enumerate([0x2406, 0x2206, 0x127f, 0x7fe, 0x14bf, 0x7fb, 0xf025, 0xa, 0x7fff]):
        tempMemory.write(0x3000 + offset, inst)
    processor.run()
    timeCost = time() - startTime
    print(f"Speed:{int(710930/timeCost/1000)} kHz")


speedTest()
