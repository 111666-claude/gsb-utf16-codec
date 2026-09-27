import io
import random
import unittest
from contextlib import redirect_stderr, redirect_stdout

from utf16codec.cli import main
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

    def test_surrogate_pair(self):
        self.assertEqual(encode("\U0001F600"), bytes.fromhex("3dd800de"))

    def test_surrogate_pair_big_endian(self):
        self.assertEqual(encode("\U0001F600", True), bytes.fromhex("d83dde00"))

    def test_boundary_codepoints(self):
        for code in (0x0000, 0xD7FF, 0xE000, 0xFFFF, 0x10000, 0x10FFFF):
            char = chr(code)
            self.assertEqual(encode(char), char.encode("utf-16-le"))
            self.assertEqual(encode(char, True), char.encode("utf-16-be"))

    def test_lone_surrogate_rejected(self):
        for code in (0xD800, 0xDBFF, 0xDC00, 0xDFFF):
            with self.assertRaises(Utf16Error):
                encode(chr(code))

    def test_encode_error_has_index(self):
        with self.assertRaises(Utf16Error) as ctx:
            encode("ab\ud800")
        self.assertEqual(ctx.exception.index, 2)


class DecodeTest(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(decode(b"A\x00"), "A")

    def test_odd_length(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"A")
        self.assertEqual(ctx.exception.index, 0)

    def test_odd_length_index(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(b"A\x00B")
        self.assertEqual(ctx.exception.index, 1)

    def test_empty(self):
        self.assertEqual(decode(b""), "")

    def test_ascii_roundtrip(self):
        self.assertEqual(decode(encode("hello")), "hello")

    def test_error_type_exists(self):
        self.assertTrue(issubclass(Utf16Error, Exception))

    def test_surrogate_pair(self):
        self.assertEqual(decode(bytes.fromhex("3dd800de")), "\U0001F600")

    def test_lone_high_surrogate(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(bytes.fromhex("3dd8"))
        self.assertEqual(ctx.exception.index, 0)

    def test_lone_low_surrogate(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(bytes.fromhex("00de"))
        self.assertEqual(ctx.exception.index, 0)

    def test_reversed_surrogates(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(bytes.fromhex("00de3dd8"))
        self.assertEqual(ctx.exception.index, 0)

    def test_high_surrogate_at_end(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(bytes.fromhex("41003dd8"))
        self.assertEqual(ctx.exception.index, 1)

    def test_high_surrogate_followed_by_plain_char(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(bytes.fromhex("3dd84100"))
        self.assertEqual(ctx.exception.index, 0)

    def test_low_surrogate_after_bom_index(self):
        with self.assertRaises(Utf16Error) as ctx:
            decode(BOM_LE + bytes.fromhex("00de"))
        self.assertEqual(ctx.exception.index, 1)


class BomTest(unittest.TestCase):
    def test_bom_le(self):
        self.assertEqual(decode(BOM_LE + "嗨\U0001F600".encode("utf-16-le")),
                         "嗨\U0001F600")

    def test_bom_be(self):
        self.assertEqual(decode(BOM_BE + "嗨\U0001F600".encode("utf-16-be")),
                         "嗨\U0001F600")

    def test_bom_only(self):
        self.assertEqual(decode(BOM_LE), "")
        self.assertEqual(decode(BOM_BE), "")

    def test_no_bom_defaults_le(self):
        self.assertEqual(decode("嗨".encode("utf-16-le")), "嗨")

    def test_no_bom_big_endian_flag(self):
        self.assertEqual(decode("嗨".encode("utf-16-be"), True), "嗨")

    def test_bom_overrides_flag(self):
        self.assertEqual(decode(BOM_LE + "A".encode("utf-16-le"), True), "A")
        self.assertEqual(decode(BOM_BE + "A".encode("utf-16-be")), "A")


class RoundtripTest(unittest.TestCase):
    def test_roundtrip_samples(self):
        samples = [
            "",
            "hello world",
            "中文测试",
            "\U0001F600\U0001F4A9",
            "\U00010000",
            "\U0010FFFF",
            "\ud7ff\ue000\uffff\U00010000\U0010ffff",
            "a\U0001F600b\U00010000c",
        ]
        for text in samples:
            self.assertEqual(decode(encode(text)), text)
            self.assertEqual(decode(encode(text, True), True), text)
            self.assertEqual(decode(BOM_LE + encode(text)), text)
            self.assertEqual(decode(BOM_BE + encode(text, True)), text)

    def test_random_against_stdlib(self):
        rng = random.Random(20260928)
        for _ in range(10000):
            length = rng.randrange(0, 20)
            chars = []
            for _ in range(length):
                while True:
                    code = rng.randrange(0, 0x110000)
                    if not 0xD800 <= code <= 0xDFFF:
                        break
                chars.append(chr(code))
            text = "".join(chars)
            self.assertEqual(encode(text), text.encode("utf-16-le"))
            self.assertEqual(encode(text, True), text.encode("utf-16-be"))
            self.assertEqual(decode(encode(text)),
                             encode(text).decode("utf-16-le"))
            self.assertEqual(decode(encode(text, True), True),
                             encode(text, True).decode("utf-16-be"))

    def test_chunk_boundary_surrogate_pair(self):
        from utf16codec.codec import _CHUNK_UNITS
        text = "a" * (_CHUNK_UNITS - 1) + "\U0001F600" + "b" * _CHUNK_UNITS
        self.assertEqual(decode(encode(text)), text)
        self.assertEqual(decode(encode(text, True), True), text)


class CliTest(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_encode_hex_emoji(self):
        code, out, _ = self.run_cli("--encode-hex", "f09f9880")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "3dd800de")

    def test_encode_hex_be(self):
        code, out, _ = self.run_cli("--encode-hex", "f09f9880", "--be")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "d83dde00")

    def test_decode_hex(self):
        code, out, _ = self.run_cli("--decode-hex", "3dd800de")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "f09f9880")

    def test_decode_hex_lone_surrogate_fails(self):
        code, _, err = self.run_cli("--decode-hex", "3dd8")
        self.assertEqual(code, 1)
        self.assertIn("0", err)

    def test_decode_hex_be(self):
        code, out, _ = self.run_cli("--decode-hex", "d83dde00", "--be")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "f09f9880")

    def test_decode_hex_bom(self):
        code, out, _ = self.run_cli("--decode-hex", "feffd83dde00")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "f09f9880")

    def test_no_args(self):
        code, _, _ = self.run_cli()
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
