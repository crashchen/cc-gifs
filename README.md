# cc-gifs

Pixel-art spinner GIF generator for Clawd, the Claude Code mascot.

这是一个围绕 Clawd 的像素风加载动图生成器仓库，重点公开的是 Python 生成脚本、词表和文档，不包含本地参考图与导出的 GIF 成品。

## Disclaimer

This repository is an unofficial technical/art experiment. The code in this repository is released under the MIT License, but `Claude`, `Claude Code`, `Clawd`, and related mascot or brand imagery remain the intellectual property and/or trademarks of Anthropic. The MIT license here applies to the repository code only and does not grant rights to Anthropic branding or character assets. Generated mascot imagery should be treated as learning/showcase material unless you have separate permission for other uses.

本仓库开源的是代码，不是 Anthropic 的品牌或角色授权。

## What’s Included

- `generate_clawd_gifs.py`: the unified generator for all official Clawd spinner scenes
- `spinner-words.md`: the full official catalog of 116 spinner words with Chinese translations and descriptions
- `CLAUDE.md` and `AGENTS.md`: working notes and agent-facing repository instructions
- `requirements.txt`: minimal runtime dependency list
- `LICENSE`: MIT license for repository code

## What’s Not Included

- Generated GIF files
- Local JPG/PNG reference images
- Other local source assets used during experimentation

Those files are intentionally ignored in git so this public repo stays lightweight and code-focused.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python3 generate_clawd_gifs.py
```

Generated GIFs are written to:

```text
generated/Clawd-{Word}.gif
```

The generator currently covers **116 official spinner words**. Most compact scenes render as 6-frame loops at 170ms per frame, while some handcrafted scenes use longer timelines.

## Project Structure

```text
.
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
├── README.md
├── generate_clawd_gifs.py
├── requirements.txt
├── spinner-words.md
└── generated/   # runtime output, ignored by git
```

## Notes on the Generator

- The script uses Pillow to draw each frame directly as pixel art.
- Clawd scenes are split between:
  - handcrafted `frames_*()` functions that return full frame lists
  - compact `sc_*()` functions wrapped by `make_frames()`
- `main()` merges both styles and exports animated transparent GIFs through `save_gif()`.

For more repo-specific implementation details, see [CLAUDE.md](./CLAUDE.md).

## Spinner Catalog

The full official word list lives in [spinner-words.md](./spinner-words.md).

It includes:

- official word numbering
- Chinese translations
- scene descriptions
- generation status tracking

## Credits

Created in collaboration with coding agents across multiple refinement passes.
