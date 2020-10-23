from Annotations import *
from re import compile as reCompile, sub
from EmuUtil import decToBin, binToDec, bitModified

# Regular opcodes
OPCODEs = ['ADD', 'AND', 'JMP', 'JSR', 'JSRR', 'LD', 'LDI', 'LDR', 'LEA', 'NOT', 'RET', 'RTI', 'ST', 'STI', 'STR', 'TRAP']
# Branch opcodes
OPCODEs += ['BRnzp', 'BRnz', 'BRnp', 'BRzp', 'BRn', 'BRz', 'BRp', 'BR']
# Assembler directives
OPCODEs += ['.ORIG', '.END', '.FILL', '.BLKW', '.STRINGZ']
# Trap Alias
OPCODEs += ['HALT', 'IN', 'OUT', 'GETC', 'PUTS']

# Regex pattern for matching OPCODE
opCodePattern = '|'.join(OPCODEs).replace('.', '\\.')

# Regex pattern for parse assembly line.
pattern = reCompile('^(?!' + opCodePattern + ')(?P<LABEL>\S+)?\s+(?P<OPCODE>' + opCodePattern + ')' + '(\s+(?P<OPERANDS>.*))?')


def parseNumber(num: Str) -> Int:
    assert num[0] in ['x', '#']
    if (num.startswith('x')):
        return int(num[1:], 16)
    elif (num.startswith('#')):
        return int(num[1:])


def parseOperands(operand: Str, symbolTable) -> List[Int]:
    if (operand == None): return []
    # Clear out spaces from operand and split it
    operandSubs = operand.replace(' ', '').split(',')
    realOperands = []
    for op in operandSubs:
        if (op[0] == 'R'):
            realOperands.append(int(op[1]))
        elif (op[0] in ['x', '#']):
            realOperands.append(parseNumber(op))
        else:
            realOperands.append(symbolTable[op])
    return realOperands


def parseOperandsFormat(operand: Str) -> Str:
    if (operand == None): return ''
    operandSubs = operand.replace(' ', '').split(',')
    return ''.join(['R' if op[0] == 'R' else 'I' for op in operandSubs])


def handleDirective(lineDetail: Dict) -> Union[Int, List[Int]]:
    if (lineDetail['OPCODE'] == '.FILL'):
        return parseNumber(lineDetail['OPERANDS'])
    elif (lineDetail['OPCODE'] == '.BLKW'):
        assert False #TODO
        return [0 for _ in range(parseNumber(lineDetail['OPERAND']))]
    elif (lineDetail['OPCODE'] == '.STRINGZ'):
        assert False #TODO
        return [ord(i) for i in lineDetail['OPERAND'][1:-1]] + [0]


def makeInstruction(template: Str, *args: List[Int]) -> Int:
    def replaceVariable(matchObj):
        index, length = matchObj.group(0)[1:-1].split(',')
        if (length[-1] == '~'):
            return decToBin(args[int(index)], int(length[:-1]), True)
        else:
            return decToBin(args[int(index)], int(length), False)

    # return bitModified(65535, 15, sub('\[\d+,\d+~?\]', replaceVariable, template))
    return binToDec(sub('\[\d+,\d+~?\]', replaceVariable, template), True)


def handleInstruction(lineDetail: Dict, symbolTable: Dict, lineno: Int) -> Int:
    operandFormat = parseOperandsFormat(lineDetail['OPERANDS'])
    realOperands = parseOperands(lineDetail['OPERANDS'], symbolTable)
    print(lineDetail, operandFormat, realOperands, lineno)
    if (lineDetail['OPCODE'] == 'ADD'):
        if (operandFormat == 'RRR'):
            return makeInstruction('0001[0,3~][1,3~]000[2,3~]', *realOperands)
        else:
            return makeInstruction('0001[0,3~][1,3~]1[2,5]', *realOperands)
    elif (lineDetail['OPCODE'] == 'AND'):
        if (operandFormat == 'RRR'):
            return makeInstruction('0101[0,3~][1,3~]000[2,3~]', *realOperands)
        else:
            return makeInstruction('0101[0,3~][1,3~]1[2,5]', *realOperands)
    elif (lineDetail['OPCODE'].startswith('BR')):
        nzpFlags = binToDec(''.join(['1' if i in lineDetail['OPCODE'] else '0' for i in 'nzp']), True)
        return makeInstruction('0000[0,3~][1,9]', nzpFlags, realOperands[0] - lineno - 1)
    elif (lineDetail['OPCODE'] == 'JMP'):
        return makeInstruction('1100000[0,3~]000000', *realOperands)
    elif (lineDetail['OPCODE'] == 'RET'):
        return makeInstruction('1100000[0,3~]000000', 7)
    elif (lineDetail['OPCODE'] == 'JSR'):
        return makeInstruction('01001[0,11]', realOperands[0] - lineno - 1)
    elif (lineDetail['OPCODE'] == 'JSRR'):
        return makeInstruction('0100000[0,3~]000000', *realOperands)
    elif (lineDetail['OPCODE'] == 'LD'):
        return makeInstruction('0010[0,3~][1,9]', realOperands[0], realOperands[1] - lineno - 1)
    return 0


def parseAssembly(asmLines: Str):
    # Clean out the comment information
    asmLines = sub('\s*;;.*', '', asmLines)
    # Split code into lines
    lines, lineInfos = asmLines.split('\n'), []
    # Program start index and address
    startAddress = (0, 0x3000)
    # Matched tokens for lines
    for line in lines:
        matched = pattern.match(line)
        if (matched == None): continue
        lineDetail = matched.groupdict()
        # Search for start index and address
        if (lineDetail['OPCODE'] == '.ORIG'):
            assert startAddress == (0, 0x3000)
            startAddress = (len(lineInfos), parseNumber(lineDetail['OPERANDS']))
        # Finish parsing
        lineInfos.append(lineDetail)
    # Build symbols table
    symbolTable, offset = {}, 0
    for index, line in enumerate(lineInfos):
        if line['OPCODE'] in ['.END']: offset -= 1
        if line['LABEL'] == None: continue
        symbolTable[line['LABEL']] = startAddress[1] + (index - startAddress[0]) + offset
    machineCodes = []
    # Translate operation into machine codes
    for index, lineDetail in enumerate(lineInfos):
        if (lineDetail['OPCODE'] == '.ORIG'):
            continue
        elif (lineDetail['OPCODE'] == '.END'): #TODO
            continue
        elif (lineDetail['OPCODE'].startswith('.')):
            result = handleDirective(lineDetail)
            if (isinstance(result, int)):
                machineCodes.append(result)
            else:
                machineCodes += result
        else:
            machineCodes.append(handleInstruction(lineDetail, symbolTable, startAddress[1] + (index - startAddress[0])))
    print([print(decToBin(i, 16, True)) for i in machineCodes])


with open('Test2.asm', 'r') as sourceFile:
    parseAssembly(sourceFile.read())
