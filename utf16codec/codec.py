"""UTF-16 编解码（BOM、代理对、截断）。只用标准库。"""

BOM_LE = b"\xff\xfe"
BOM_BE = b"\xfe\xff"


class Utf16Error(Exception):
    """UTF-16 不合法。缺陷：不带字节偏移。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def encode(text, big_endian=False):
    """编码。缺陷：每个码点只取低 16 位，代理对不拆开。"""
    out = bytearray()
    for char in text:
        code = ord(char)
        # 缺陷：> 0xFFFF 的码点被截成低 16 位，没有生成代理对
        unit = code & 0xFFFF
        if big_endian:
            out.append(unit >> 8)
            out.append(unit & 0xFF)
        else:
            out.append(unit & 0xFF)
            out.append(unit >> 8)
    return bytes(out)


def decode(data):
    """解码。缺陷：不校验孤立代理，也不处理 BOM。"""
    if len(data) % 2 != 0:
        raise Utf16Error("数据长度不是偶数")
    units = []
    for index in range(0, len(data), 2):
        units.append(data[index] | (data[index + 1] << 8))
    out = []
    for unit in units:
        # 缺陷：孤立代理直接当成普通码点
        out.append(chr(unit))
    return "".join(out)
