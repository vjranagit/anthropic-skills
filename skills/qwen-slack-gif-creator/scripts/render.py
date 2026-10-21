# Copyright 2026 Usman Mustafa
#!/usr/bin/env python3
"""Render content.json into a looping 480x480 Slack GIF.

Layout is decided here, never by the content author:
  - links contain a loop  -> "ring": items on an ellipse in loop order, group colour legend row
  - otherwise             -> "lanes": one horizontal lane per group, flow top to bottom
Every step lights its `on` items together; pulses run along links from the previous
step's items, and the caption clock turns once per loop, so the seam is continuous.
Text sizes are fixed (>= 17 px); anything that does not fit fails with a one-line FIX hint.
"""
import contextlib, json, math, os, sys
from PIL import Image, ImageDraw, ImageFont

W = H = 480
FPS, STEP_FRAMES, MOVE_FRAMES = 10, 14, 6
TOP, BOT, LEFT, RIGHT = 64, 384, 24, 456          # diagram area
HEAD_W, BOX_H, MAX_BOX_W, PAD, GAP = 96, 54, 168, 14, 12
MAX_GROUPS, MAX_PER_GROUP, MAX_ITEMS, MAX_RING, MAX_STEPS = 4, 3, 12, 8, 8
BG, CARD, EDGE, TEXT, DARK, BAND = (17, 31, 48), (25, 48, 69), (98, 128, 150), (239, 244, 243), (14, 26, 38), (20, 38, 56)
PALETTE = [(63, 205, 170), (245, 183, 72), (240, 120, 104), (150, 160, 250)]
FONT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print('FIX: ' + msg, file=sys.stderr)
    sys.exit(2)


def font(size):
    return ImageFont.truetype(os.path.join(FONT_DIR, 'DejaVuSansCondensed-Bold.ttf'), size)


TITLE_F, ITEM_F, NOTE_F, HEAD_F = font(26), font(20), font(20), font(17)
_MEASURE = ImageDraw.Draw(Image.new('RGB', (1, 1)))


def tw(text, f):
    return _MEASURE.textlength(text, font=f)


def chars_per(width, f):
    return int(width / tw('abcdefghijklmnopqrstuvwxyz', f) * 26)


def wrap(text, f, width, max_lines):
    lines, cur = [], ''
    for word in text.split():
        trial = (cur + ' ' + word).strip()
        if tw(trial, f) <= width:
            cur = trial
            continue
        if not cur or tw(word, f) > width:
            return None
        lines.append(cur)
        cur = word
    if cur:
        lines.append(cur)
    return lines if 0 < len(lines) <= max_lines else None


def fit(text, f, width, max_lines, what):
    lines = wrap(text, f, width, max_lines)
    if lines is None:
        fail(f'{what} {text!r} does not fit: use at most {max_lines} line(s) of ~{chars_per(width, f)} characters')
    return lines


def label_width(text, max_inner, what):
    """Narrowest inner width that fits text in 2 lines, or fail."""
    w = max(tw(word, ITEM_F) for word in text.split())
    while w <= max_inner:
        if wrap(text, ITEM_F, w, 2):
            return math.ceil(w)
        w += 2
    fit(text, ITEM_F, max_inner, 2, what)


def load(path):
    try:
        c = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        fail(f'content is not valid JSON ({e}); start again from templates/content.json')
    for key in ('title', 'groups', 'links', 'steps'):
        if key not in c:
            fail(f'missing "{key}": keep every key of templates/content.json')
    if not isinstance(c['title'], str) or not c['title'].strip():
        fail('"title" must be a non-empty string')
    groups = c['groups']
    if not isinstance(groups, list) or not 1 <= len(groups) <= MAX_GROUPS:
        fail(f'"groups" needs 1-{MAX_GROUPS} groups; merge minor groups')
    items, group_of = [], {}
    for gi, g in enumerate(groups):
        if not isinstance(g, dict) or not isinstance(g.get('name'), str) or not isinstance(g.get('items'), list):
            fail('each group must be {"name": "...", "items": ["...", ...]}')
        if not 1 <= len(g['items']) <= MAX_PER_GROUP:
            fail(f'group {g["name"]!r} has {len(g["items"])} items; use 1-{MAX_PER_GROUP} (split it into two groups)')
        for it in g['items']:
            if not isinstance(it, str) or not it.strip():
                fail(f'group {g["name"]!r} has an empty or non-text item')
            if it in group_of:
                fail(f'item {it!r} appears twice; every item label must be unique')
            group_of[it] = gi
            items.append(it)
    if not 3 <= len(items) <= MAX_ITEMS:
        fail(f'{len(items)} items in total; use 3-{MAX_ITEMS}')
    links = c['links']
    if not isinstance(links, list):
        fail('"links" must be a list of ["from item", "to item"] pairs')
    for ln in links:
        if not (isinstance(ln, list) and len(ln) == 2):
            fail(f'link {ln!r} must be ["from item", "to item"]')
        for end in ln:
            if end not in group_of:
                fail(f'link {ln!r} names unknown item {end!r}; use an exact item label')
        if ln[0] == ln[1]:
            fail(f'link {ln!r} points to itself; remove it')
    if len({tuple(l) for l in links}) != len(links):
        fail('a link is listed twice; remove the duplicate')
    steps = c['steps']
    if not isinstance(steps, list) or not 2 <= len(steps) <= MAX_STEPS:
        fail(f'"steps" needs 2-{MAX_STEPS} steps')
    for k, s in enumerate(steps, 1):
        if not isinstance(s, dict) or not isinstance(s.get('on'), list) or not s['on'] or not isinstance(s.get('note'), str) or not s['note'].strip():
            fail(f'step {k} must be {{"on": ["item", ...], "note": "..."}} with at least one item and a note')
        for it in s['on']:
            if it not in group_of:
                fail(f'step {k} turns on unknown item {it!r}; use an exact item label')
    return c, items, group_of, [tuple(l) for l in links], steps


def find_cycle_exists(items, adj):
    state = {}

    def visit(u):
        state[u] = 1
        for v in adj[u]:
            if state.get(v) == 1 or (v not in state and visit(v)):
                return True
        state[u] = 2
        return False
    return any(u not in state and visit(u) for u in items)


def longest_cycle(items, adj):
    best = []

    def dfs(path, seen):
        nonlocal best
        for v in adj[path[-1]]:
            if v == path[0] and len(path) > len(best):
                best = list(path)
            elif v not in seen:
                dfs(path + [v], seen | {v})
    for u in items:
        dfs([u], {u})
    return best


def ring_order(items, links, adj, first):
    cyc = longest_cycle(items, adj)
    if first in cyc:
        i = cyc.index(first)
        cyc = cyc[i:] + cyc[:i]
    order = list(cyc)
    def score(o):   # most links between ring neighbours, then shortest links overall
        dist = [min(abs(o.index(a) - o.index(b)), len(o) - abs(o.index(a) - o.index(b))) for a, b in links if a in o and b in o]
        return (dist.count(1), -sum(dist))
    for u in items:
        if u not in order:
            order = max((order[:i] + [u] + order[i:] for i in range(1, len(order) + 1)), key=score)
    return order


def overlap(a, b, m=0):
    return a[0] - m < b[2] and b[0] - m < a[2] and a[1] - m < b[3] and b[1] - m < a[3]


def inside(p, r, m=0):
    return r[0] - m <= p[0] <= r[2] + m and r[1] - m <= p[1] <= r[3] + m


def layout_lanes(groups):
    heads = [fit(g['name'], HEAD_F, HEAD_W - 14, 2, 'group name') for g in groups]
    area_l, area_r = LEFT + max(56, max(tw(l, HEAD_F) for h in heads for l in h) + 22), RIGHT - 8
    rows = []
    for g in groups:
        n = len(g['items'])
        room = area_r - area_l - (n - 1) * GAP
        need = [label_width(it, min(MAX_BOX_W, room) - PAD, 'item') + PAD for it in g['items']]
        if sum(need) > room:
            fail(f'lane {g["name"]!r} is too crowded: shorten its item labels or move one item to another group')
        extra = (room - sum(need)) / n
        widths = [min(MAX_BOX_W, w + extra) for w in need]
        lines = max(len(wrap(it, ITEM_F, w - PAD + 1, 2)) for it, w in zip(g['items'], widths))
        rows.append((widths, lines * 23 + 10))
    total = sum(h + 12 for _, h in rows)
    ng = len(groups)
    gap = min(56, (BOT - TOP - total) / (ng - 1)) if ng > 1 else 0
    y = TOP + (BOT - TOP - total - (ng - 1) * gap) / 2
    boxes, bands = {}, []
    for gi, (g, (widths, bh)) in enumerate(zip(groups, rows)):
        x = area_l + (area_r - area_l - sum(widths) - (len(widths) - 1) * GAP) / 2
        for it, bw in zip(g['items'], widths):
            boxes[it] = (x, y + 6, x + bw, y + 6 + bh)
            x += bw + GAP
        bands.append(((LEFT, y, RIGHT, y + bh + 12), heads[gi], PALETTE[gi]))
        y += bh + 12 + gap
    return boxes, bands


def layout_ring(order):
    n = len(order)
    width = {it: max(100, label_width(it, MAX_BOX_W - PAD, 'item') + PAD) for it in order}
    top = TOP + 24                          # room for the legend row
    cx, cy = W / 2, (top + BOT) / 2
    rx, ry = (RIGHT - LEFT - max(width.values())) / 2, (BOT - top - BOX_H) / 2
    for shift in (0.0, 0.5):
        boxes, ang = {}, {}
        for i, it in enumerate(order):
            a = -math.pi / 2 + 2 * math.pi * (i + shift) / n
            x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
            boxes[it] = (x - width[it] / 2, y - BOX_H / 2, x + width[it] / 2, y + BOX_H / 2)
            ang[it] = a
        bl = list(boxes.values())
        if not any(overlap(bl[i], bl[j], 6) for i in range(n) for j in range(i + 1, n)):
            return boxes, ang, (cx, cy, rx, ry)
    fail(f'the {n} loop items collide: shorten the longest item labels or drop an item')


def trim(pts, src, dst):
    s = 0
    while s < len(pts) and inside(pts[s], src, 4):
        s += 1
    e = len(pts)
    while e > s and inside(pts[e - 1], dst, 4):
        e -= 1
    return pts[s:e]


def straight(a, b):
    (x0, y0), (x1, y1) = a, b
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 2))
    return [(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n) for t in range(n + 1)]


def inward(a, b, ell):
    """Chord bent toward the ring centre so it clears the items between a and b."""
    cx, cy = ell[0], ell[1]
    k = (cx + ((a[0] + b[0]) / 2 - cx) * 0.2, cy + ((a[1] + b[1]) / 2 - cy) * 0.2)
    n = max(2, int((math.hypot(k[0] - a[0], k[1] - a[1]) + math.hypot(b[0] - k[0], b[1] - k[1])) / 2))
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * k[0] + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * k[1] + t * t * b[1]) for t in (i / n for i in range(n + 1))]


def arc(ell, a0, a1):
    cx, cy, rx, ry = ell
    n = max(8, int(abs(a1 - a0) * max(rx, ry) / 2))
    return [(cx + rx * math.cos(a0 + (a1 - a0) * t / n), cy + ry * math.sin(a0 + (a1 - a0) * t / n)) for t in range(n + 1)]


def offset(pts, d):
    out = []
    for i, (x, y) in enumerate(pts):
        (xa, ya), (xb, yb) = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        L = math.hypot(xb - xa, yb - ya) or 1
        out.append((x - (yb - ya) / L * d, y + (xb - xa) / L * d))
    return out


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def ports(links, boxes):
    """Lanes: spread a box's links along its bottom/top edge, ordered by where they go."""
    peers = {}
    for u, v in links:
        a, b = boxes[u], boxes[v]
        if b[1] > a[3] or b[3] < a[1]:
            peers.setdefault((u, 'out'), []).append(v)
            peers.setdefault((v, 'in'), []).append(u)
    xs = {}
    for (it, _), ps in peers.items():
        ps.sort(key=lambda p: center(boxes[p])[0])
        r = boxes[it]
        for k, p in enumerate(ps):
            xs[(it, p)] = r[0] + (r[2] - r[0]) * (k + 1) / (len(ps) + 1)
    return xs


def route(links, boxes, mode, order, ang, ell):
    paths = {}
    pairs, port = set(links), ports(links, boxes) if mode == 'lanes' else {}
    for u, v in links:
        if mode == 'ring':
            n = len(order)
            i, j = order.index(u), order.index(v)
            step = 2 * math.pi / n
            if (j - i) % n == 1:
                pts = arc(ell, ang[u], ang[u] + step)
            elif (i - j) % n == 1:
                pts = arc(ell, ang[u], ang[u] - step)
            else:
                pts = inward(center(boxes[u]), center(boxes[v]), ell)
        else:   # lanes: leave through the bottom/top edge so steep lines clear lane neighbours
            (ux, uy), (vx, vy), a, b = center(boxes[u]), center(boxes[v]), boxes[u], boxes[v]
            if b[1] > a[3]:
                pts = straight((port[(u, v)], a[3]), (port[(v, u)], b[1]))
            elif b[3] < a[1]:
                pts = straight((port[(u, v)], a[1]), (port[(v, u)], b[3]))
            else:
                pts = straight((ux, uy), (vx, vy))
        if (v, u) in pairs:
            pts = offset(pts, 7)
        pts = trim(pts, boxes[u], boxes[v])
        if len(pts) < 4:
            fail(f'items {u!r} and {v!r} are too close to link; put them in different groups')
        for w, r in boxes.items():
            if w not in (u, v) and any(inside(p, r, 3) for p in pts):
                fail(f'link {u!r}->{v!r} runs under item {w!r}; link items in neighbouring groups or reorder items inside groups')
        paths[(u, v)] = pts
    return paths


def legend_row(groups):
    """Ring mode: colour chips for the groups in one row under the title."""
    chips, x = [], LEFT + 4
    for gi, g in enumerate(groups):
        name = fit(g['name'], HEAD_F, RIGHT - LEFT, 1, 'group name')[0]
        chips.append((x, name, PALETTE[gi]))
        x += 20 + tw(name, HEAD_F) + 18
    if x - 18 > RIGHT:
        fail('group names are too long for one legend row: shorten them (~10 characters each)')
    return chips


def arrow(d, pts, col, width):
    d.line(pts, fill=col, width=width, joint='curve')
    (x0, y0), (x1, y1) = pts[-4], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    tip = (x1 + 2 * math.cos(a), y1 + 2 * math.sin(a))
    d.polygon([tip, (tip[0] - 12 * math.cos(a - 0.45), tip[1] - 12 * math.sin(a - 0.45)),
               (tip[0] - 12 * math.cos(a + 0.45), tip[1] - 12 * math.sin(a + 0.45))], fill=col)


def at(pts, t):
    i = min(len(pts) - 1, max(0, int(t * (len(pts) - 1))))
    return pts[i]


def blend(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    content, out = sys.argv[1], sys.argv[2]
    skill_root = os.environ.get('SLACK_GIF_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, skill_root)
    from core.gif_builder import GIFBuilder
    from core.validators import validate_gif

    c, items, group_of, links, steps = load(content)
    groups = c['groups']
    title = fit(c['title'], TITLE_F, RIGHT - LEFT - 8, 1, 'title')[0]
    adj = {u: [b for a, b in links if a == u] for u in items}
    notes = [fit(s['note'], NOTE_F, RIGHT - 92 - 10, 2, f'step {k} note') for k, s in enumerate(steps, 1)]

    if find_cycle_exists(items, adj):
        if len(items) > MAX_RING:
            fail(f'links form a loop, and a loop fits at most {MAX_RING} items (have {len(items)}); merge or drop minor items')
        mode = 'ring'
        order = ring_order(items, links, adj, steps[0]['on'][0])
        boxes, ang, ell = layout_ring(order)
        bands = []
    else:
        mode, order, ang, ell = 'lanes', items, {}, None
        boxes, bands = layout_lanes(groups)
    labels = {it: fit(it, ITEM_F, boxes[it][2] - boxes[it][0] - PAD + 1, 2, 'item') for it in items}
    paths = route(links, boxes, mode, order, ang, ell)
    legend = legend_row(groups) if mode == 'ring' else []

    n = len(steps)
    total = n * STEP_FRAMES
    on = [set(s['on']) for s in steps]
    frames_dir = os.path.join(out, 'frames')
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        if f.startswith('step_') and f.endswith('.png'):
            os.remove(os.path.join(frames_dir, f))
    b = GIFBuilder(width=W, height=H, fps=FPS)
    for fi in range(total):
        k, local = divmod(fi, STEP_FRAMES)
        prev, cur = on[k - 1], on[k]
        t = min(1.0, local / MOVE_FRAMES)
        moving = [(u, v) for (u, v) in links if u in prev and v in cur]
        if moving and t < 1.0:   # sources stay lit until their pulses land on the targets
            active = prev | (cur - {v for (u, v) in moving})
        else:
            active = cur
        hot = set(moving) | {(u, v) for (u, v) in links if u in cur and v in cur}

        im = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((12, 12, 468, 468), radius=22, fill=CARD, outline=(77, 190, 186), width=3)
        d.text((LEFT + 4, 36), title, font=TITLE_F, fill=TEXT, anchor='lm')
        for rect, head, col in bands:
            d.rounded_rectangle(rect, radius=12, fill=blend(CARD, col, 0.10), outline=blend(CARD, col, 0.45), width=2)
            hy = (rect[1] + rect[3]) / 2 - (len(head) - 1) * 10
            for li, line in enumerate(head):
                d.text((LEFT + 10, hy + li * 20), line, font=HEAD_F, fill=col, anchor='lm')
        for ln, pts in paths.items():
            if ln not in hot:
                arrow(d, pts, EDGE, 3)
        for ln in hot:
            arrow(d, paths[ln], (250, 236, 170), 4)
        for it in items:
            col = PALETTE[group_of[it]]
            lit = it in active
            d.rounded_rectangle(boxes[it], radius=10, fill=col if lit else BAND, outline=col, width=3)
            x, y = center(boxes[it])
            ls = labels[it]
            for li, line in enumerate(ls):
                d.text((x, y + (li - (len(ls) - 1) / 2) * 23), line, font=ITEM_F, fill=DARK if lit else TEXT, anchor='mm')
        if t < 1.0:
            ease = 0.5 - 0.5 * math.cos(math.pi * t)
            for ln in moving:
                px, py = at(paths[ln], ease)
                d.ellipse((px - 8, py - 8, px + 8, py + 8), fill=(255, 250, 220), outline=DARK, width=2)
        for x, name, col in legend:
            d.rounded_rectangle((x, TOP + 3, x + 14, TOP + 17), radius=3, fill=col)
            d.text((x + 20, TOP + 10), name, font=HEAD_F, fill=TEXT, anchor='lm')
        # caption: clock turns once per loop (continuous at the seam), one tick per step
        d.rounded_rectangle((LEFT, 394, RIGHT, 458), radius=12, fill=BAND)
        ccx, ccy, cr = LEFT + 34, 426, 22
        d.ellipse((ccx - cr, ccy - cr, ccx + cr, ccy + cr), outline=EDGE, width=2)
        for s in range(n):
            a = -math.pi / 2 + 2 * math.pi * s / n
            col = (250, 236, 170) if s == k else EDGE
            d.ellipse((ccx + (cr - 1) * math.cos(a) - 4, ccy + (cr - 1) * math.sin(a) - 4,
                       ccx + (cr - 1) * math.cos(a) + 4, ccy + (cr - 1) * math.sin(a) + 4), fill=col)
        a = -math.pi / 2 + 2 * math.pi * fi / total
        d.line((ccx, ccy, ccx + (cr - 6) * math.cos(a), ccy + (cr - 6) * math.sin(a)), fill=(250, 236, 170), width=3)
        ls = notes[k]
        for li, line in enumerate(ls):
            d.text((LEFT + 68, 426 + (li - (len(ls) - 1) / 2) * 24), line, font=NOTE_F, fill=TEXT, anchor='lm')
        b.add_frame(im)
        if local == STEP_FRAMES - 1:
            im.save(os.path.join(frames_dir, f'step_{k + 1:02d}.png'))

    gif = os.path.join(out, 'animation.gif')
    with open(os.path.join(out, 'build.log'), 'w') as log, contextlib.redirect_stdout(log):
        b.save(gif, num_colors=96, remove_duplicates=False)
        ok, info = validate_gif(gif, is_emoji=False, verbose=True)
    if not ok:
        fail(f'Slack validator rejected the GIF: {info}')
    with Image.open(gif) as im:
        frames = im.n_frames
    print(json.dumps({'ok': True, 'gif': os.path.abspath(gif), 'layout': mode, 'items': len(items),
                      'links': len(links), 'steps': n, 'frames': frames, 'duration_s': round(total / FPS, 1),
                      'step_frames': sorted(os.listdir(frames_dir))}))


if __name__ == '__main__':
    main()
