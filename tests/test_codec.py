import unittest

from utf16codec.codec import Utf16Error, decode, encode


class EncodeTest(unittest.TestCase):
    def test_ascii_little_endian(self):
        self.assertEqual(encode("A"), b"A\x00")

    def test_ascii_big_endian(self):
        self.assertEqual(encode("A", True), b"\x00A")

    def test_empty(self):
        self.assertEqual(encode(""), b"")

    def test_length_is_even(self):
        self.assertEqual(len(encode("hello")) % 2, 0)


class DecodeTest(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(decode(b"A\x00"), "A")

    def test_odd_length(self):
        with self.assertRaises(Utf16Error):
            decode(b"A")

    def test_empty(self):
        self.assertEqual(decode(b""), "")

    def test_ascii_roundtrip(self):
        self.assertEqual(decode(encode("hello")), "hello")

    def test_error_type_exists(self):
        self.assertTrue(issubclass(Utf16Error, Exception))
