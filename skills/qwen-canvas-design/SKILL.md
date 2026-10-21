---
name: qwen-canvas-design
description: Create an original technical poster as PNG that maps a system's parts and their relationships, using Anthropic canvas-design guidance. Trigger for static art, posters, and editorial one-page visuals.
---
# Qwen Canvas Design
1. Copy `templates/content.json` and replace values only. Split the topic into 2–5 `groups` (subsystems or parallel lanes), each with 1–4 `parts`: `name` ≤28 and `note` ≤60 characters. Give each fact its own part; do not merge two subtopics into one note. Part names must be unique.
2. Add up to 12 `links` `{from, to, label}` using exact part names for every real relationship (flows, drives, controls, measures). Point each link from cause to effect. `label` ≤18 is optional. A link back to an earlier part is drawn dashed as feedback; an unlabeled link between neighbours in one group is a short arrow.
3. Keep movement/title/subtitle/takeaway ≤24/48/90/90 characters. Never add coordinates, sizes or colours; the script does all layout.
4. Run `scripts/make.sh <content-file> <out-dir>` from this skill directory.
5. Read the one-line JSON result. If `ok` is false, apply its `fix` and rerun.
6. Open the PNG and check the facts and text readability. This compact renderer lays out parts in lanes; relationship links are validated but not routed.

| Common failure | Fix |
|---|---|
| Text or label does not fit | Follow the `fix` hint: shorten the text. |
| Link to unknown part | Copy `from`/`to` exactly from a part `name`. |
| Missing font/Pillow | Run `scripts/setup.sh`, then make.sh. |

Content template: `templates/content.json`.
