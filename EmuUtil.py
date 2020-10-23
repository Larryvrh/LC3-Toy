from Annotations import *
from math import ceil

binToHexMap = {bin(i)[2:].zfill(4): hex(i)[2:] for i in range(16)}
hexToBinMap = {v: k for k, v in binToHexMap.items()}


def fill(string: Str, char: Str, size: Int, reverse=False) -> Str:
    length = len(string)
    if size <= length: return string
    if not reverse:
        return ''.join([char for _ in range(size - length)]) + string
    else:
        return string + ''.join([char for _ in range(size - length)])


def decToBin(num: Int, fillTo: Int = -1, unsigned=False) -> Str:
    if (unsigned):
        return fill(bin(num)[2:], '0', fillTo)
    binRes = '0' + bin(num if num >= 0 else -num)[2:]
    if num < 0:
        tailIndex = binRes.rfind('1')
        binRes = ''.join(['1' if i == '0' else '0' for i in binRes[:tailIndex]]) + binRes[tailIndex:]
    return fill(binRes, binRes[0], fillTo)


def binToDec(num: Str, unsigned=False) -> Int:
    if num[0] == '0' or unsigned:
        return int(num, 2)
    tailIndex = num.rfind('1')
    return -int(''.join(['1' if i == '0' else '0' for i in num[:tailIndex]]) + num[tailIndex:], 2)


def hexToBin(num: Str) -> Str:
    return ''.join([hexToBinMap[c] for c in num])


def binToHex(num: Str) -> Str:
    numFilled = fill(num, num[0], ceil(len(num) / 4) * 4)
    return ''.join([binToHexMap[numFilled[i * 4:i * 4 + 4]] for i in range(len(numFilled) // 4)])


def decToHex(num: Str) -> Str:
    return binToHex(decToBin(num))


def hexToDec(num: Str) -> Str:
    return binToDec(hexToBin(num))


def setBit(value, index, bit):
    mask = 1 << index
    value &= ~mask
    if bit: value |= mask
    return value


def bitModified(value: Int, tailIndex: Int, newBits: Str) -> Int:
    for i, bit in enumerate(newBits):
        value = setBit(value, tailIndex - i, int(bit))
    return value