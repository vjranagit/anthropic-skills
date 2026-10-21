# Qwen Slack GIF creator

A weak-model wrapper for local LLMs, tuned on qwen3.8-27b, that turns a system description into an animated Slack GIF.

## Install and use

Run `scripts/setup.sh` once. Copy `templates/content.json` to `<out-dir>/content.json`, replace values, then run `scripts/make.sh <content-file> <out-dir>` from this directory. Prompt pattern: “Use the qwen-slack-gif-creator skill to make a Slack GIF about: [topic].”

## Results

Best version: attempt 2 (v2), overall 5.8/10; attempt scores: v1 4.0, v2 5.8, v3 5.5. Scores are an AI critic's assessment, not benchmarks. Example: [GIF poster](examples/slack-gif.png); example input: [content](examples/content.json).

## License

Upstream Apache-2.0 license applies to the renderer components; see `LICENSE.txt`. The files are modified for this wrapper as noted in `NOTICE.txt`, satisfying section 4(b). The bundled font has separate terms in `DEJAVU-FONT-LICENSE.txt`.
