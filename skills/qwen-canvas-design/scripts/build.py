# Copyright 2026 Usman Mustafa
"""Render a content-only technical poster from the qwen-canvas-design schema."""
import json
import pathlib
import sys
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]
FONT_DIR = ROOT
W, H_MIN, H_MAX, M = 2160, 2700, 3840, 120
INK, MUTED, TEAL, BACK, LINE, BG = '#0F172A', '#475569', '#0D9488', '#C2410C', '#334155', '#F8FAFC'
TINTS = [('#E3F2EF', '#0D9488'), ('#E6ECF7', '#2F5DA8'), ('#F5ECDF', '#9A5B13'), ('#EDE7F5', '#6D4AA8'), ('#E8F0DF', '#4D7C0F')]
TEXT_MAX = {'movement': 24, 'title': 48, 'subtitle': 90, 'takeaway': 90}

def font(bold, size):
    return ImageFont.truetype(str(FONT_DIR / ('WorkSans-Bold.ttf' if bold else 'WorkSans-Regular.ttf')), size)

def main():
    d = json.loads(pathlib.Path(sys.argv[1]).read_text())
    for key, limit in TEXT_MAX.items():
        if len(d.get(key, '')) > limit:
            print(json.dumps({'ok': False, 'error': f'{key} exceeds {limit} characters', 'fix': f'Shorten {key}.'})); return
    groups, parts = d['groups'], []
    if not 2 <= len(groups) <= 5:
        raise ValueError('Use 2–5 groups')
    for group in groups:
        if not 1 <= len(group['parts']) <= 4:
            raise ValueError('Use 1–4 parts per group')
        parts.extend(group['parts'])
    names = [p['name'] for p in parts]
    if len(set(names)) != len(names) or any(len(p['name']) > 28 or len(p.get('note', '')) > 60 for p in parts):
        raise ValueError('Part names must be unique (28 characters maximum), notes 60 maximum')
    links = d.get('links', [])
    if len(links) > 12 or any(l['from'] not in names or l['to'] not in names for l in links):
        raise ValueError('Links must use known part names; maximum 12')
    w, h, margin = 2160, 3100, 120
    im = Image.new('RGB', (w, h), '#F8FAFC'); draw = ImageDraw.Draw(im)
    draw.text((margin, margin), d.get('movement', 'SYSTEM MAP').upper(), fill='#0D9488', font=font(True, 42))
    draw.text((margin, margin+80), d.get('title', 'System map'), fill='#0F172A', font=font(True, 96))
    draw.text((margin, margin+210), d.get('subtitle', ''), fill='#475569', font=font(False, 46))
    y, lane_h = margin+360, (h-margin-360-220)//len(groups)
    for gi, group in enumerate(groups):
        tint, color = TINTS[gi%len(TINTS)]; draw.rounded_rectangle((margin,y,w-margin,y+lane_h-28), radius=24, fill=tint)
        draw.text((margin+30,y+20), group['name'], fill=color, font=font(True, 50))
        bw = (w-2*margin-60-(len(group['parts'])-1)*28)//len(group['parts'])
        for pi,p in enumerate(group['parts']):
            x=margin+30+pi*(bw+28); yy=y+100
            draw.rounded_rectangle((x,yy,x+bw,yy+210), radius=18, fill='white', outline=color, width=4)
            draw.text((x+20,yy+18),p['name'],fill='#0F172A',font=font(True,44))
            draw.text((x+20,yy+86),p.get('note',''),fill='#475569',font=font(False,36))
        y += lane_h
    draw.text((margin,h-180),d.get('takeaway',''),fill='#0F172A',font=font(True,46))
    out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
    png,pdf=out/'poster.png',out/'poster.pdf'; im.save(png); im.save(pdf,resolution=300)
    print(json.dumps({'ok':True,'png':str(png),'pdf':str(pdf),'width':w,'height':h,'groups':len(groups),'parts':len(parts),'links':len(links)}))
if __name__ == '__main__': main()
