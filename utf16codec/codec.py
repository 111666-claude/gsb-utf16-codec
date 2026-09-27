"""UTF-16 编解码（BOM、代理对、截断校验）。只用标准库。

错误信息中的「单元下标」均为 0 起的 16 位单元序号，按剥掉 BOM 之后的
载荷计数（即单元 i 对应原始字节偏移 2*(i+bom_units)）。
"""

import array
import io

BOM_LE = b"\xff\xfe"
BOM_BE = b"\xfe\xff"

_HIGH_MIN = 0xD800
_HIGH_MAX = 0xDBFF
_LOW_MIN = 0xDC00
_LOW_MAX = 0xDFFF

_CHUNK = 4096


class Utf16Error(Exception):
    """UTF-16 不合法。``unit_index`` 是出错单元的 0 起下标。"""

    def __init__(self, message, unit_index=None):
        if unit_index is not None:
            message = "%s（单元下标 %d）" % (message, unit_index)
        super().__init__(message)
        self.message = message
        self.unit_index = unit_index


def encode(text, big_endian=False):
    """把字符串编成 UTF-16（无 BOM）。

    BMP 之外的码点（U+10000..U+10FFFF）拆成高/低代理对，结果逐字节等价于
    ``text.encode("utf-16-le")`` / ``text.encode("utf-16-be")``。
    输入若含孤立代理（U+D800..U+DFFF）则按单元下标报错。
    单遍输出，内存 O(输出)。
    """
    out = bytearray()
    units = array.array("H")

    def tobytes(arr):
        if big_endian:
            arr.byteswap()
        return arr.tobytes()
    for index, char in enumerate(text):
        code = ord(char)
        if code < 0x10000:
            if _HIGH_MIN <= code <= _LOW_MAX:
                raise Utf16Error(
                    "输入字符串含孤立代理 U+%04X，无法编入 UTF-16" % code, index
                )
            units.append(code)
        else:
            code -= 0x10000
            units.append(0xD800 | (code >> 10))
            units.append(0xDC00 | (code & 0x3FF))
        if len(units) >= _CHUNK:
            out += tobytes(units)
            units = array.array("H")
    out += tobytes(units)
    return bytes(out)


def decode(data, big_endian=False):
    """把 UTF-16 字节解成字符串。

    - ``FF FE`` 开头按小端、``FE FF`` 开头按大端并剥掉 BOM；无 BOM 时按
      ``big_endian`` 决定字节序。
    - 高代理（D800..DBFF）后必须紧跟低代理（DC00..DFFF）；孤立代理、顺序
      颠倒、高代理后直接结束或后跟普通单元都按单元下标报错。
    - 字节长度（BOM 之外）不是偶数时报错。
    单遍扫描、增量写入，内存 O(输出)。
    """
    view = memoryview(data)

    bom_units = 0
    if view[:2] == BOM_LE:
        big_endian = False
        view = view[2:]
        bom_units = 1
    elif view[:2] == BOM_BE:
        big_endian = True
        view = view[2:]
        bom_units = 1

    length = len(view)
    if length % 2 != 0:
        raise Utf16Error(
            "数据长度不是偶数，最后一个 16 位单元被截断",
            length // 2,
        )

    def read_unit(pos):
        if big_endian:
            return (view[pos] << 8) | view[pos + 1]
        return view[pos] | (view[pos + 1] << 8)

    writer = io.StringIO()
    pending_high = None
    chunk = []
    for pos in range(0, length, 2):
        unit_index = pos // 2
        unit = read_unit(pos)

        if pending_high is not None:
            if _LOW_MIN <= unit <= _LOW_MAX:
                code = 0x10000 + (((pending_high - 0xD800) << 10) | (unit - 0xDC00))
                chunk.append(chr(code))
            elif _HIGH_MIN <= unit <= _HIGH_MAX:
                raise Utf16Error(
                    "高代理 U+%04X 后又出现高代理 U+%04X，应为低代理"
                    % (pending_high, unit),
                    unit_index,
                )
            else:
                raise Utf16Error(
                    "高代理 U+%04X 后出现普通单元 U+%04X，应为低代理"
                    % (pending_high, unit),
                    unit_index,
                )
            pending_high = None
        elif _HIGH_MIN <= unit <= _HIGH_MAX:
            pending_high = unit
        elif _LOW_MIN <= unit <= _LOW_MAX:
            raise Utf16Error(
                "出现孤立低代理 U+%04X，前面没有高代理" % unit, unit_index
            )
        else:
            chunk.append(chr(unit))

        if len(chunk) >= _CHUNK:
            writer.write("".join(chunk))
            chunk.clear()

    if pending_high is not None:
        raise Utf16Error(
            "高代理 U+%04X 位于末尾，后面缺少低代理" % pending_high,
            length // 2 - 1,
        )

    if chunk:
        writer.write("".join(chunk))
    return writer.getvalue()
