"""UTF-16 编解码（BOM、代理对、截断）。只用标准库。"""

import io
import struct
from array import array

BOM_LE = b"\xff\xfe"
BOM_BE = b"\xfe\xff"

_CHUNK_UNITS = 1 << 16

if array("H").itemsize != 2:  # pragma: no cover
    raise RuntimeError("需要 16 位 unsigned short 的平台")


class Utf16Error(Exception):
    """UTF-16 不合法。index 是出错的 16 位单元下标（BOM 占下标 0）。"""

    def __init__(self, message, index=None):
        self.index = index
        if index is not None:
            message = "%s（单元下标 %d）" % (message, index)
        super().__init__(message)
        self.message = message


def encode(text, big_endian=False):
    """把 str 编成 UTF-16 字节（不含 BOM），与 str.encode('utf-16-le/be') 一致。"""
    out = bytearray()
    units = array("H")
    for index, char in enumerate(text):
        code = ord(char)
        if code <= 0xFFFF:
            if 0xD800 <= code <= 0xDFFF:
                raise Utf16Error("孤立代理 U+%04X 不能编码" % code, index)
            units.append(code)
        else:
            code -= 0x10000
            units.append(0xD800 | (code >> 10))
            units.append(0xDC00 | (code & 0x3FF))
        if len(units) >= _CHUNK_UNITS:
            _flush_units(units, out, big_endian)
    _flush_units(units, out, big_endian)
    return bytes(out)


def _flush_units(units, out, big_endian):
    if not units:
        return
    if big_endian:
        units.byteswap()
    out += units.tobytes()
    del units[:]


def decode(data, big_endian=False):
    """把 UTF-16 字节解成 str。BOM 优先，无 BOM 时按 big_endian。"""
    if len(data) % 2 != 0:
        raise Utf16Error("数据长度不是偶数", len(data) // 2)
    offset = 0
    if data[:2] == BOM_LE:
        big_endian = False
        offset = 1
        data = data[2:]
    elif data[:2] == BOM_BE:
        big_endian = True
        offset = 1
        data = data[2:]
    fmt = ">%dH" if big_endian else "<%dH"
    text = io.StringIO()
    chars = []
    pending_high = 0
    pending_index = -1
    unit_index = offset
    for start in range(0, len(data), _CHUNK_UNITS * 2):
        chunk = data[start:start + _CHUNK_UNITS * 2]
        for unit in struct.unpack(fmt % (len(chunk) // 2), chunk):
            if pending_index >= 0:
                if 0xDC00 <= unit <= 0xDFFF:
                    chars.append(chr(0x10000 + ((pending_high - 0xD800) << 10)
                                     + (unit - 0xDC00)))
                    pending_index = -1
                else:
                    raise Utf16Error(
                        "高代理 U+%04X 后没有紧跟低代理" % pending_high,
                        pending_index)
            elif 0xD800 <= unit <= 0xDBFF:
                pending_high = unit
                pending_index = unit_index
            elif 0xDC00 <= unit <= 0xDFFF:
                raise Utf16Error("孤立低代理 U+%04X" % unit, unit_index)
            else:
                chars.append(chr(unit))
            unit_index += 1
        if len(chars) >= _CHUNK_UNITS:
            text.write("".join(chars))
            del chars[:]
    if pending_index >= 0:
        raise Utf16Error("高代理 U+%04X 后数据结束" % pending_high, pending_index)
    text.write("".join(chars))
    return text.getvalue()
