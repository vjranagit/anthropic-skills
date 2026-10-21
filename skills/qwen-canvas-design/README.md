# Qwen Canvas Design

A weak-model wrapper for local LLMs, tuned on qwen3.8-27b, that turns a system description into a technical poster.

## Install and use

Run `scripts/setup.sh` once. Copy `templates/content.json` and replace its values, then run `scripts/make.sh <content-file> <out-dir>` from this directory. Prompt pattern: “Use the qwen-canvas-design skill to make a technical poster about: [topic].”

## Results

Best version: attempt 2 (v2), overall 6.7/10; attempt scores: v1 4.5, v2 6.7, v3 5.0. Scores are an AI critic's assessment, not benchmarks. Example: [poster](examples/canvas.png); example input: [content](examples/content.json).

## License

Upstream Anthropic canvas-design license terms apply (see `skills/canvas-design/SKILL.md`). The bundled Work Sans fonts are licensed under SIL OFL 1.1; see `WorkSans-OFL.txt`.
