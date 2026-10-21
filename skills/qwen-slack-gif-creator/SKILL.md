---
name: qwen-slack-gif-creator
description: Create a looping 480x480 Slack GIF that shows a system's parts, groups, links and timed steps (parallel, branching or cyclic). Use when asked for a Slack GIF.
---
# Qwen Slack GIF creator
You write CONTENT only. `scripts/make.sh` picks layout, sizes, colours and motion.

1. Copy `templates/content.json` to `<out-dir>/content.json` and replace every value for your topic:
   - `title`: at most 30 characters.
   - `groups`: 1-4 groups (subsystems, sides, phases). Each has 1-3 `items`; one item = one real part, actor or state, at most 20 characters. 3-12 items in total, all labels different.
   - `links`: `["from item", "to item"]` for every real flow or cause. A link back to an earlier item makes a loop; the script then draws a ring (at most 8 items).
   - `steps`: 2-8 moments in time order; the GIF repeats from the last step to the first. `on` = the items acting at that moment. `note` = what happens, with its key number, at most 60 characters.
2. Accuracy: one fact per field. Do not mix measurements and events in one label. Separate moments are separate steps; only things that happen together share a step.
3. Run `scripts/make.sh <content-file> <out-dir>`. If it prints `FIX: ...`, apply exactly that and rerun until it prints `{"ok": true, ...}`.
4. Check all requested parts and relations appear. Outputs are `<out-dir>/animation.gif` and `<out-dir>/frames/step_NN.png`.

Run `scripts/setup.sh` first. Renderer components from Anthropic's slack-gif-creator are modified for this wrapper; see `LICENSE.txt` and `NOTICE.txt`. Bundled DejaVu font license: `DEJAVU-FONT-LICENSE.txt`.
