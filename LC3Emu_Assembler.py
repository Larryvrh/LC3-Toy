from re import compile as reCompile, sub

from Annotations import *
from LC3Emu_Util import decToBin, binToDec

# Regular opcodes
OPCODEs = ['ADD', 'AND', 'JMP', 'JSR', 'JSRR', 'LDI', 'LDR', 'LD', 'LEA', 'NOT', 'RET', 'RTI', 'STI', 'STR', 'ST', 'TRAP']
# Branch opcodes
OPCODEs += ['BRnzp', 'BRnz', 'BRnp', 'BRzp', 'BRn', 'BRz', 'BRp', 'BR']
# Trap Alias
OPCODEs += ['HALT', 'IN', 'OUT', 'GETC', 'PUTS']
# Real opcodes
realOPCODEs = OPCODEs.copy()
# Assembler directives
OPCODEs += ['.ORIG', '.END', '.FILL', '.BLKW', '.STRINGZ']

# Regex pattern for matching OPCODE
opCodePattern = '|'.join(OPCODEs).replace('.', '\\.')
opCodePatternEx = ' |'.join(OPCODEs).replace('.', '\\.')

# Regex pattern for parse assembly line.
pattern = reCompile(f'(^(?!{opCodePatternEx})(?P<LABEL>\S+))?\s*(?P<OPCODE>{opCodePattern})?' + '(\s+(?P<OPERANDS>.*))?')


def parseNumber(num: Str) -> Int:
    assert num[0] in ['x', '#'] or num[0].isdigit()
    if num.startswith('x'):
        return int(num[1:], 16)
    elif num.startswith('0x'):
        return int(num[2:], 16)
    elif num.startswith('#'):
        return int(num[1:])
    elif num[0].isdigit():
        return int(num)


def parseOperands(operand: Str, symbolTable, lineNo) -> List[Int]:
    if operand is None: return []
    # Clear out spaces from operand and split it
    operandSubs = operand.replace(' ', '').split(',')
    realOperands = []
    for op in operandSubs:
        if op[0] == 'R' and op[1].isdigit():
            realOperands.append(int(op[1]))
        elif op[0] in ['x', '#']:
            realOperands.append(parseNumber(op))
        else:
            realOperands.append(symbolTable[op] - lineNo - 1)
    return realOperands


def parseOperandsFormat(operand: Str) -> Str:
    if operand is None: return ''
    operandSubs = operand.replace(' ', '').split(',')
    return ''.join(['R' if op[0] == 'R' else 'I' for op in operandSubs])


def handleDirective(lineDetail: Dict, symbolTable: Dict) -> Union[Int, List[Int]]:
    if lineDetail['OPCODE'] == '.FILL':
        if lineDetail['OPERANDS'] in symbolTable:
            return symbolTable[lineDetail['OPERANDS']]
        return parseNumber(lineDetail['OPERANDS'])
    elif lineDetail['OPCODE'] == '.BLKW':
        return [0 for _ in range(parseNumber(lineDetail['OPERANDS']))]
    elif lineDetail['OPCODE'] == '.STRINGZ':
        return [ord(i) for i in lineDetail['OPERANDS'][1:-1]] + [0]


def makeInstruction(template: Str, *args: List[Int]) -> Int:
    def replaceVariable(matchObj):
        index, length = matchObj.group(0)[1:-1].split(',')
        if length[-1] == '~':
            return decToBin(args[int(index)], int(length[:-1]), True)
        else:
            return decToBin(args[int(index)], int(length), False)

    # return bitModified(65535, 15, sub('\[\d+,\d+~?\]', replaceVariable, template))
    return binToDec(sub('\[\d+,\d+~?\]', replaceVariable, template), True)


def handleInstruction(lineDetail: Dict, symbolTable: Dict, lineno: Int) -> Int:
    operandFormat = parseOperandsFormat(lineDetail['OPERANDS'])
    realOperands = parseOperands(lineDetail['OPERANDS'], symbolTable, lineno)
    # print(lineDetail, operandFormat, realOperands, lineno)
    if lineDetail['OPCODE'] == 'ADD':
        if operandFormat == 'RRR':
            return makeInstruction('0001[0,3~][1,3~]000[2,3~]', *realOperands)
        else:
            return makeInstruction('0001[0,3~][1,3~]1[2,5]', *realOperands)
    elif lineDetail['OPCODE'] == 'AND':
        if operandFormat == 'RRR':
            return makeInstruction('0101[0,3~][1,3~]000[2,3~]', *realOperands)
        else:
            return makeInstruction('0101[0,3~][1,3~]1[2,5]', *realOperands)
    elif lineDetail['OPCODE'].startswith('BR'):
        nzpFlags = binToDec(''.join(['1' if i in lineDetail['OPCODE'] else '0' for i in 'nzp']), True)
        if lineDetail['OPCODE'] == 'BR':
            nzpFlags = binToDec('111', True)
        return makeInstruction('0000[0,3~][1,9]', nzpFlags, realOperands[0])
    elif lineDetail['OPCODE'] == 'JMP':
        return makeInstruction('1100000[0,3~]000000', *realOperands)
    elif lineDetail['OPCODE'] == 'RET':
        return makeInstruction('1100000[0,3~]000000', 7)
    elif lineDetail['OPCODE'] == 'JSR':
        return makeInstruction('01001[0,11]', realOperands[0])
    elif lineDetail['OPCODE'] == 'JSRR':
        return makeInstruction('0100000[0,3~]000000', *realOperands)
    elif lineDetail['OPCODE'] == 'LD':
        return makeInstruction('0010[0,3~][1,9]', realOperands[0], realOperands[1])
    elif lineDetail['OPCODE'] == 'LDI':
        return makeInstruction('1010[0,3~][1,9]', realOperands[0], realOperands[1])
    elif lineDetail['OPCODE'] == 'LDR':
        return makeInstruction('0110[0,3~][1,3~][2,6]', realOperands[0], realOperands[1], realOperands[2])
    elif lineDetail['OPCODE'] == 'LEA':
        return makeInstruction('1110[0,3~][1,9]', realOperands[0], realOperands[1])
    elif lineDetail['OPCODE'] == 'NOT':
        return makeInstruction('1001[0,3~][1,3~]111111', realOperands[0], realOperands[1])
    elif lineDetail['OPCODE'] == 'RTI':
        return makeInstruction('1000000000000000')
    elif lineDetail['OPCODE'] == 'ST':
        return makeInstruction('0011[0,3~][1,9]', realOperands[0], realOperands[1])
    elif lineDetail['OPCODE'] == 'STI':
        return makeInstruction('1011[0,3~][1,9]', realOperands[0], realOperands[1])
    elif lineDetail['OPCODE'] == 'STR':
        return makeInstruction('0111[0,3~][1,3~][2,6]', realOperands[0], realOperands[1], realOperands[2])
    elif lineDetail['OPCODE'] == 'TRAP':
        return makeInstruction('11110000[0,8~]', realOperands[0])
    elif lineDetail['OPCODE'] == 'HALT':
        return makeInstruction('11110000[0,8~]', 0x25)
    elif lineDetail['OPCODE'] == 'IN':
        return makeInstruction('11110000[0,8~]', 0x23)
    elif lineDetail['OPCODE'] == 'OUT':
        return makeInstruction('11110000[0,8~]', 0x21)
    elif lineDetail['OPCODE'] == 'GETC':
        return makeInstruction('11110000[0,8~]', 0x20)
    elif lineDetail['OPCODE'] == 'PUTS':
        return makeInstruction('11110000[0,8~]', 0x22)
    return 0


def buildAddressTable(lineInfos: Dict):
    baseAddr, occupiedBytes = (0, 0x3000), 0
    symbolTable = {}
    for i, lineDetail in enumerate(lineInfos):
        lineDetail.update({'ADDR': occupiedBytes})
        opCode = lineDetail['OPCODE']
        if opCode == '.ORIG':
            baseAddr = (i, parseNumber(lineDetail['OPERANDS']))
            continue
        elif opCode in realOPCODEs:
            occupiedBytes += 1
        elif opCode == '.FILL':
            occupiedBytes += 1
        elif opCode == '.BLKW':
            occupiedBytes += parseNumber(lineDetail['OPERANDS'])
        elif opCode == '.STRINGZ':
            occupiedBytes += len(lineDetail['OPERANDS']) - 1
    for lineDetail in lineInfos:
        lineDetail['ADDR'] += (baseAddr[1] - baseAddr[0])
        if lineDetail['LABEL'] is not None:
            symbolTable[lineDetail['LABEL']] = lineDetail['ADDR']
    return symbolTable


def parseAssembly(asmLines: Str):
    # Clean out the comment information
    asmLines = sub('\s*;.*', '', asmLines)
    # Split code into lines
    lines, lineInfos = asmLines.split('\n'), []
    # Matched tokens for lines
    for line in lines:
        matched = pattern.match(line)
        if matched is None: continue
        lineDetail = matched.groupdict()
        # print(lineDetail)
        if set(lineDetail.values()) == {None}: continue
        # print(line, '\n', lineDetail)
        if lineDetail['LABEL'] is not None and lineDetail['LABEL'][-1] == ':':
            lineDetail['LABEL'] = lineDetail['LABEL'][:-1]
        if lineDetail['LABEL'] in OPCODEs:
            lineDetail['OPCODE'] = lineDetail['LABEL']
            lineDetail['LABEL'] = None
        # Finish parsing
        lineInfos.append(lineDetail)
    # print('>',lineInfos)
    # Build symbols table TODO: Need to be fixed for multi-byte allocation
    symbolTable = buildAddressTable(lineInfos)
    machineCodes = []
    # Translate operation into machine codes
    for index, lineDetail in enumerate(lineInfos):
        if lineDetail['OPCODE'] is None:
            continue
        elif lineDetail['OPCODE'] == '.ORIG':
            continue
        elif lineDetail['OPCODE'] == '.END':
            break
        elif lineDetail['OPCODE'].startswith('.'):
            result = handleDirective(lineDetail, symbolTable)
            if isinstance(result, int):
                machineCodes.append(result)
            else:
                machineCodes += result
        else:
            machineCodes.append(handleInstruction(lineDetail, symbolTable, lineDetail['ADDR']))
    print('[' + ','.join([(hex(i)) for i in machineCodes]) + ']')
    print({k:hex(v) for k,v in symbolTable.items()})
    return machineCodes


with open('Test.asm', 'r', encoding='utf-8') as sourceFile:
    parseAssembly(sourceFile.read())
