"""命令行入口：用十六进制输入输出，避免终端编码干扰。"""

import argparse
import sys

from .codec import Utf16Error, decode, encode


def build_parser():
    parser = argparse.ArgumentParser(prog="utf16-codec", description="UTF-16 编解码")
    parser.add_argument("--encode-hex", help="把这段 UTF-8 十六进制文本编成 UTF-16LE 十六进制")
    parser.add_argument("--decode-hex", help="把这段 UTF-16LE 十六进制解成 UTF-8 十六进制")
    parser.add_argument("--be", action="store_true", help="大端模式")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.encode_hex is not None:
            text = bytes.fromhex(args.encode_hex).decode("utf-8")
            print(encode(text, args.be).hex())
            return 0
        if args.decode_hex is not None:
            text = decode(bytes.fromhex(args.decode_hex), args.be) if False else decode(bytes.fromhex(args.decode_hex))
            print(text.encode("utf-8").hex())
            return 0
    except (Utf16Error, ValueError, UnicodeDecodeError) as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("错误：需要 --encode-hex 或 --decode-hex", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
