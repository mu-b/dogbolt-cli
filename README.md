# dogbolt-cli

A CLI for [dogbolt.org](https://dogbolt.org). Uploads a binary and downloads
decompiled source files.

## Install

```
pip install dogbolt-cli
```

Or from source:

```
pip install .
```

## Usage

```
db -f <binary> [-o <output-dir>] [-d <decompilers>] [-v]
```

| Option | Description |
|---|---|
| `-f`, `--file-path` | Path to the binary (required, max 2 MB) |
| `-o`, `--output-dir` | Directory to save results (default: `src/` next to the binary) |
| `-d`, `--decompilers` | Comma-separated list of decompilers (default: BinaryNinja,Ghidra,Hex-Rays) |
| `-v`, `--verbose` | Print additional info, including all decompilers available on the API |

### Example

```
$ db -f test
src/binary-ninja.c
src/ghidra.c
src/hex-rays.c
```

With `-v` to see progress and all decompilers available from the API:

```
$ db -f test -v
db: uploading test (15760 bytes)
db: binary id: 874c5de3-a98d-40d4-bae3-14ce5cadbe69
db: available decompilers: BinaryNinja, Boomerang, Ghidra, Hex-Rays, RecStudio, Reko, Relyze, RetDec, Snowman, angr, dewolf
db: using decompilers: BinaryNinja, Ghidra, Hex-Rays
db: fetching results...
db: fetched 1/3, retrying in 30s
db: fetching results...
src/binary-ninja.c
src/ghidra.c
db: fetched 2/3, retrying in 30s
db: fetching results...
src/hex-rays.c
```

## Credits

- mu-b — [github.com/mu-b](https://github.com/mu-b)
- itachichrist — [github.com/itachicoders](https://github.com/itachicoders)
- Jacek Wielemborek
- Inspired by [dogbolt-cli-client-bash](https://github.com/milahu/dogbolt-cli-client-bash)
