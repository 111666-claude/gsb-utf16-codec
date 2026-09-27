import random
import unittest

from utf16codec.codec import BOM_BE, BOM_LE, Utf16Error, decode, encode


class EncodeTest(unittest.TestCase):
    def test_ascii_little_endian(self):
        self.assertEqual(encode("A"), b"A\x00")

    def test_ascii_big_endian(self):
        self.assertEqual(encode("A", True), b"\x00A")

    def test_empty(self):
        self.assertEqual(encode(""), b"")

    def test_length_is_even(self):
        self.assertEqual(len(encode("hello")) % 2, 0)

    def test_emoji_surrogate_pair_little_endian(self):
        # U+1F600 -> 高代理 D83D + 低代理 DE00，小端：3d d8 00 de
        self.assertEqual(encode("\U0001F600").hex(), "3dd800de")

    def test_emoji_surrogate_pair_big_endian(self):
        self.assertEqual(encode("\U0001F600", True).hex(), "d83dde00")

    def test_supplementary_boundaries(self):
        self.assertEqual(encode("\U00010000"), b"\x00\xd8\x00\xdc")
        self.assertEqual(encode("\U00010000", True), b"\xd8\x00\xdc\x00")
        self.assertEqual(encode("\U0010FFFF").hex(), "ffdbffdf")
        self.assertEqual(encode("\U0010FFFF", True).hex(), "dbffdfff")

    def test_lone_surrogate_in_input_rejected_with_index(self):
        # chr(0xD800) 是孤立高代理；下标 2 出错
        with self.assertRaises(Utf16Error) as ctx:
            encode("ab" + chr(0xD800) + "d")
        self.assertEqual(ctx.exception.unit_index, 2)
        with self.assertRaises(Utf16Error) as ctx:
            encode("x" + chr(0xDFFF))
        self.assertEqual(ctx.exception.unit_index, 1)

    def test_matches_stdlib_random(self):
        rng = random.Random(20260927)
        alphabet = (
            [0x00, 0x7F, 0x80, 0x7FF, 0x800, 0xFFFF, 0xD7FF, 0xE000]
            + [0x10000, 0x10001, 0xFFFFF, 0x100000, 0x10FFFF]
            + list(range(0x20, 0x7F))
        )
        for _ in range(2000):
            text = "".join(chr(rng.choice(alphabet)) for _ in range(rng.randrange(0, 24)))
            self.assertEqual(encode(text), text.encode("utf-16-le"))
            self.assertEqual(encode(text, True), text.encode("utf-16-be"))


class DecodeTest(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(decode(b"A\x00"), "A")

    def test_odd_length(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"A")
        self.assertEqual(ctx.exception.unit_index, 0)

    def test_odd_length_after_bom(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(BOM_LE + b"A")
        self.assertEqual(ctx.exception.unit_index, 0)

    def test_empty(self):
        self.assertEqual(decode(b""), "")

    def test_ascii_roundtrip(self):
        self.assertEqual(decode(encode("hello")), "hello")

    def test_error_type_exists(self):
        self.assertTrue(issubclass(Utf16Error, Exception))

    def test_surrogate_pair_roundtrip(self):
        for text in ("\U0001F600", "a\U0001F600b\U0010FFFF\U00010000"):
            self.assertEqual(decode(encode(text)), text)
            self.assertEqual(decode(encode(text, True), True), text)

    def test_lone_high_surrogate(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"\x3d\xd8")  # D83D，高代理后直接结束
        self.assertEqual(ctx.exception.unit_index, 0)
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"A\x00\x3d\xd8")
        self.assertEqual(ctx.exception.unit_index, 1)

    def test_lone_low_surrogate(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"\x00\xde")  # DE00，孤立低代理
        self.assertEqual(ctx.exception.unit_index, 0)
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"A\x00\x00\xde")
        self.assertEqual(ctx.exception.unit_index, 1)

    def test_high_followed_by_high(self):
        # D83D 后又跟 D800，顺序颠倒
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"\x3d\xd8\x00\xd8")
        self.assertEqual(ctx.exception.unit_index, 1)

    def test_high_followed_by_plain_unit(self):
        # D83D 后跟普通单元 0041
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"\x3d\xd8\x41\x00")
        self.assertEqual(ctx.exception.unit_index, 1)

    def test_bom_little_endian_stripped(self):
        self.assertEqual(decode(BOM_LE + b"A\x00"), "A")
        self.assertEqual(decode(BOM_LE + b"\x3d\xd8\x00\xde"), "\U0001F600")

    def test_bom_big_endian_stripped(self):
        self.assertEqual(decode(BOM_BE + b"\x00A"), "A")
        self.assertEqual(decode(BOM_BE + b"\xd8\x3d\xde\x00"), "\U0001F600")

    def test_bom_overrides_flag(self):
        self.assertEqual(decode(BOM_BE + b"\x00A", big_endian=False), "A")
        self.assertEqual(decode(BOM_LE + b"A\x00", big_endian=True), "A")

    def test_bom_only(self):
        self.assertEqual(decode(BOM_LE), "")
        self.assertEqual(decode(BOM_BE), "")

    def test_no_bom_uses_flag(self):
        self.assertEqual(decode(b"\x00A", big_endian=True), "A")
        self.assertEqual(decode(b"A\x00", big_endian=False), "A")

    def test_interior_bom_is_code_point(self):
        # 载荷中的 FEFF 是普通码点 U+FEFF
        self.assertEqual(decode(b"A\x00\xff\xfe"), "A\ufeff")

    def test_lone_surrogate_after_bom_index(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(BOM_LE + b"A\x00\x3d\xd8")
        # 下标按剥掉 BOM 后的载荷计数
        self.assertEqual(ctx.exception.unit_index, 1)

    def test_matches_stdlib_random(self):
        rng = random.Random(20260928)
        alphabet = (
            [0x00, 0x7F, 0x80, 0x7FF, 0x800, 0xFFFF, 0xD7FF, 0xE000, 0xFEFF]
            + [0x10000, 0x10001, 0xFFFFF, 0x100000, 0x10FFFF]
            + list(range(0x20, 0x7F))
        )
        for _ in range(3000):
            text = "".join(chr(rng.choice(alphabet)) for _ in range(rng.randrange(0, 24)))
            if text[:1] == "﻿":
                text = "x" + text[1:]
            self.assertEqual(decode(encode(text)), text)
            self.assertEqual(decode(encode(text, True), True), text)
            self.assertEqual(decode(encode(text)), text.encode("utf-16-le").decode("utf-16-le"))
            self.assertEqual(
                decode(encode(text, True), True),
                text.encode("utf-16-be").decode("utf-16-be"),
            )

    def test_random_data_against_stdlib_with_bom(self):
        rng = random.Random(20260929)
        for _ in range(1000):
            text = "".join(chr(rng.randrange(0, 0x110000)) for _ in range(rng.randrange(0, 16)))
            text = "".join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
            if rng.random() < 0.5:
                data = BOM_LE + text.encode("utf-16-le")
                expected = (BOM_LE + text.encode("utf-16-le")).decode("utf-16")
            else:
                data = BOM_BE + text.encode("utf-16-be")
                expected = (BOM_BE + text.encode("utf-16-be")).decode("utf-16")
            self.assertEqual(decode(data), expected)


class RoundTripTest(unittest.TestCase):
    def test_boundary_codepoints(self):
        points = [0, 1, 0x7F, 0x80, 0x7FF, 0x800, 0xD7FF, 0xE000, 0xFFFF,
                  0x10000, 0x10001, 0xFFFFE, 0xFFFFF, 0x100000, 0x10FFFE, 0x10FFFF]
        text = "".join(chr(p) for p in points) + "😀中文\U0001F600"
        self.assertEqual(decode(encode(text)), text)
        self.assertEqual(decode(encode(text, True), True), text)

    def test_ten_thousand_random_strings(self):
        rng = random.Random(424242)
        for i in range(10000):
            text = "".join(
                chr(cp)
                for _ in range(rng.randrange(0, 12))
                for cp in [rng.randrange(0, 0x110000)]
                if not (0xD800 <= cp <= 0xDFFF)
            )
            self.assertEqual(encode(text), text.encode("utf-16-le"))
            self.assertEqual(encode(text, True), text.encode("utf-16-be"))
            self.assertEqual(decode(text.encode("utf-16-le")), text)
            self.assertEqual(decode(text.encode("utf-16-be"), True), text)
            self.assertEqual(decode(encode(text)), text)


if __name__ == "__main__":
    unittest.main()
