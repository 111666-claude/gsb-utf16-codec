# utf16-codec

UTF-16 编解码（BOM、代理对、截断校验），只用 Python 标准库。

```
python3 -m utf16codec.cli --encode-hex f09f9880
python3 -m utf16codec.cli --decode-hex 3dd8
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **BMP 之外的码点要拆成代理对**：`U+1F600`（UTF-8 是 `f09f9880`）按口径编成 `3dd800de`
  （高代理 `D83D` + 低代理 `DE00`），现在只取低 16 位给 `00f6`。
- **解码要校验代理对**：高代理后面必须跟低代理，孤立代理（`3dd8`、`00de`）、顺序颠倒、
  高代理后直接结束都要报错并给出**单元下标**。
- BOM：`FFFE` 开头按小端、`FEFF` 开头按大端并剥掉；没有 BOM 时按 `--be` 决定字节序；
  数据长度不是偶数要报错。
- 不变量：`decode(encode(s)) == s`（含 BMP 内外的字符、emoji、代理对边界 `U+10000`/`U+10FFFF`）；
  `encode` 对同一输入逐字节确定；空输入给空。
- 与标准库对照：`str.encode("utf-16-le")` 等价于 `encode(s)`（不含 BOM），
  `bytes.decode("utf-16-le")` 等价于 `decode(b)`。
- 规模：100 MB 单遍编解码，内存 O(输出)。

## 现在的行为

- `encode` 对每个码点做 `code & 0xFFFF`：`U+1F600` 变成 `00f6`，代理对完全没生成。
- `decode` 把每个 16 位单元直接 `chr()`：孤立代理会被当成普通码点（转 UTF-8 时才会崩），
  也不看 BOM、不区分字节序。
- 只有「长度是奇数」被校验，其它错误都没有位置信息。

## 计划新增的能力

```
--encode-hex 文本    用 UTF-8 十六进制传输入
--decode-hex 字节    用 UTF-16 十六进制传输入
--be                 大端模式
```

## 输出

```
UTF-16 十六进制 / UTF-8 十六进制
```

## 目录

```
utf16codec/codec.py   编解码与代理对
utf16codec/cli.py     命令行入口
tests/                unittest 用例
```
