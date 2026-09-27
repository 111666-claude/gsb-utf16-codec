# utf16-codec

UTF-16 编解码（BOM、代理对、截断校验），只用 Python 标准库。

```
python3 -m utf16codec.cli --encode-hex f09f9880
python3 -m utf16codec.cli --decode-hex 3dd8
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **BMP 之外的码点要拆成代理对**：`U+1F600`（UTF-8 是 `f09f9880`）按口径编成 `3dd800de`
  （高代理 `D83D` + 低代理 `DE00`），与 `str.encode("utf-16-le")` 一致。
- **解码要校验代理对**：高代理后面必须跟低代理，孤立代理（`3dd8`、`00de`）、顺序颠倒、
  高代理后直接结束都要报错并给出**单元下标**。
- BOM：`FFFE` 开头按小端、`FEFF` 开头按大端并剥掉；没有 BOM 时按 `--be` 决定字节序；
  数据长度不是偶数要报错。
- 不变量：`decode(encode(s)) == s`（含 BMP 内外的字符、emoji、代理对边界 `U+10000`/`U+10FFFF`）；
  `encode` 对同一输入逐字节确定；空输入给空。
- 与标准库对照：`str.encode("utf-16-le")` 等价于 `encode(s)`（不含 BOM），
  `bytes.decode("utf-16-le")` 等价于 `decode(b)`。
- 规模：100 MB 单遍编解码，内存 O(输出)。

## 实现说明

- `encode` 对 BMP 之外的码点（`U+10000`..`U+10FFFF`）生成高/低代理对，逐字节等价于
  标准库 `str.encode("utf-16-le"/"utf-16-be")`；输入字符串若含孤立代理（`U+D800`..`U+DFFF`）报错。
- `decode` 严格校验代理对：高代理后必须紧跟低代理；孤立代理、顺序颠倒、高代理后直接结束、
  高代理后跟普通单元都抛 `Utf16Error`，错误带 `unit_index`（剥掉 BOM 后、0 起的 16 位单元下标）。
- BOM 决定字节序并被剥掉（`FF FE` 小端 / `FE FF` 大端），无 BOM 时按 `--be`；长度非偶数报错。
- 单遍流式处理（`array.array('H')`/`StringIO` 按 4096 单元分块），内存 O(输出)，
  不会先整份转成 list；100 MB 输入编解码均为秒级。

## 命令行参数

```
--encode-hex 文本    用 UTF-8 十六进制传输入
--decode-hex 字节    用 UTF-16 十六进制传输入（无 BOM 时按 --be 决定字节序）
--be                 大端模式（仅在输入没有 BOM 时生效）
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
