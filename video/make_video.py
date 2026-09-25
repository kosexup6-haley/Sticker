"""Render "我怎麼看世界" — a little pixel crab shows how Claude "sees".

Usage: python3 video/make_video.py   (needs pillow, numpy, imageio-ffmpeg)
Output: video/how_i_see.mp4
"""
import math
import os
import random
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "how_i_see.mp4")

W, H, FPS, SR = 1280, 720, 30, 44100
BG = (247, 240, 229)          # cream
INK = (62, 46, 40)            # warm dark brown
ORANGE = (217, 119, 87)
TEAL = (72, 150, 160)
PINK = (236, 120, 140)
PAPER = (255, 251, 244)
EYE = (38, 28, 26)

CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
f_cap = ImageFont.truetype(CJK, 36)
f_bub = ImageFont.truetype(CJK, 32)
f_big = ImageFont.truetype(CJK, 52)
f_tok = ImageFont.truetype(CJK, 30)
f_small = ImageFont.truetype(CJK, 20)
f_rgb = ImageFont.truetype(MONO, 11)
f_id = ImageFont.truetype(MONO, 15)
f_z = ImageFont.truetype(MONO, 34)

random.seed(7)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x*x*(3 - 2*x)


def back_out(x):
    """Ease with a little overshoot — makes things 'pop'."""
    x = clamp(x)
    c = 1.9
    return 1 + (c + 1)*(x - 1)**3 + c*(x - 1)**2


def fade(t, t0, t1, d=0.4):
    return clamp((t - t0)/d) * clamp((t1 - t)/d)


def mix(c, a, base=BG):
    return tuple(int(base[i] + (c[i] - base[i])*a) for i in range(3))


def text_c(d, xy, s, font, color, a=1.0, anchor="mm"):
    if a > 0.01 and s:
        d.text(xy, s, font=font, fill=mix(color, a), anchor=anchor)


def caption(d, t, items, y=H-60):
    for t0, t1, s in items:
        text_c(d, (W//2, y), s, f_cap, INK, fade(t, t0, t1))


def typewriter(s, t, t0, cps=10):
    return s[:int(clamp((t - t0)*cps, 0, len(s)))]


# ---------- the crab ----------
# 12 x 8 grid: body cols 2-9 rows 0-5, arms cols 0-1/10-11, legs cols 2,4,7,9 rows 6-7
CRAB_GRID = [
    "..XXXXXXXX..",
    "..XXXXXXXX..",
    "..XEXXXXEX..",
    "XXXEXXXXEXXX",
    "XXXXXXXXXXXX",
    "..XXXXXXXX..",
    "..X.X..X.X..",
    "..X.X..X.X..",
]
GROWS, GCOLS = len(CRAB_GRID), len(CRAB_GRID[0])
CELL_COLOR = {".": PAPER, "X": ORANGE, "E": EYE}
EYE_CELLS = [(r, c) for r in range(GROWS) for c in range(GCOLS) if CRAB_GRID[r][c] == "E"]


def draw_crab(d, cx, by, s, blink=False, walk=None, wave=0.0, look=0, a=1.0):
    """cx = centre x, by = bottom y, s = pixel size."""
    x0, y0 = cx - 6*s, by - 8*s
    col = mix(ORANGE, a)

    def px(c, r, color=col, h=1):
        d.rectangle((x0 + c*s, y0 + r*s, x0 + (c+1)*s - 1, y0 + (r+h)*s - 1), fill=color)

    d.rectangle((x0 + 2*s, y0, x0 + 10*s - 1, y0 + 6*s - 1), fill=col)
    for side, cols in ((0, (0, 1)), (1, (10, 11))):
        up = 1 if wave and (side == 0) == (math.sin(wave) > 0) else 0
        for c in cols:
            px(c, 3 - up, h=2)
    for i, c in enumerate((2, 4, 7, 9)):
        short = walk is not None and (i % 2) == (int(walk) % 2)
        px(c, 6, h=1 if short else 2)
    for (r, c) in ((2, 3), (2, 8)):
        c += look
        if blink:
            d.rectangle(
                (x0 + c*s, y0 + 3*s + s//2 - max(2, s//8), x0 + (c+1)*s - 1, y0 + 3*s + s//2 + max(2, s//8)),
                fill=mix(EYE, a))
        else:
            px(c, r, mix(EYE, a), h=2)


def draw_heart(d, cx, cy, s, color, a=1.0):
    rows = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "X":
                x, y = cx + (c - 3.5)*s, cy + (r - 3)*s
                d.rectangle((x, y, x + s - 1, y + s - 1), fill=mix(color, a))


def bubble(d, x, y, text, a, tail_to, font=f_bub):
    if a <= 0.01:
        return
    w = d.textlength(text, font=font) + 48
    h = 64
    box = (x - w/2, y - h/2, x + w/2, y + h/2)
    tx, ty = tail_to
    d.polygon([(x - 18, y + h/2 - 2), (x + 10, y + h/2 - 2), (tx, ty)], fill=mix(PAPER, a), outline=None)
    d.rounded_rectangle(box, radius=22, fill=mix(PAPER, a), outline=mix(INK, a), width=3)
    d.polygon([(x - 16, y + h/2 - 3), (x + 8, y + h/2 - 3), (tx, ty)], fill=mix(PAPER, a))
    d.line([(x - 18, y + h/2), (tx, ty), (x + 10, y + h/2)], fill=mix(INK, a), width=3)
    text_c(d, (x, y), text, font, INK, a)


def blinking(t, period=2.7, phase=0.0):
    return ((t + phase) % period) < 0.13


# ---------- number grid (the crab portrait as I receive it) ----------
def draw_rgb_cell(d, x, y, size, r, c, a=1.0):
    color = CELL_COLOR[CRAB_GRID[r][c]]
    d.rectangle((x, y, x + size - 2, y + size - 2), fill=mix(color, 0.28*a))
    ink = mix(tuple(int(v*0.6) for v in color) if color != PAPER else (150, 140, 128), a)
    for k, v in enumerate(color):
        d.text((x + size/2 - 1, y + size/2 + (k - 1)*(size*0.26)), str(v), font=f_rgb, fill=ink, anchor="mm")


FLIP = [(r, c) for r in range(GROWS) for c in range(GCOLS)]
random.shuffle(FLIP)
SCATTER = {rc: (random.uniform(-100, W + 100), random.uniform(-150, H + 150), random.uniform(-1, 1)) for rc in FLIP}
LAND_ORDER = sorted(FLIP, key=lambda rc: random.random())
LAND_RANK = {rc: i for i, rc in enumerate(LAND_ORDER)}

PS = 44                                   # portrait pixel size
PX0, PY0 = (W - GCOLS*PS)//2, 110         # portrait top-left


def portrait(d, x0, y0, s, a=1.0):
    d.rectangle((x0 - 24, y0 - 24, x0 + GCOLS*s + 24, y0 + GROWS*s + 64), fill=mix(PAPER, a),
                outline=mix((210, 196, 180), a), width=2)
    for r in range(GROWS):
        for c in range(GCOLS):
            if CRAB_GRID[r][c] != ".":
                d.rectangle((x0 + c*s, y0 + r*s, x0 + (c+1)*s - 1, y0 + (r+1)*s - 1),
                            fill=mix(CELL_COLOR[CRAB_GRID[r][c]], a, PAPER))


# ---------- tokens ----------
TOKENS = ["做", "一個", "視頻", "，", "展示", "你", "用", "眼睛", "看", "世界", "的", "方式", "！"]
TOK_IDS = [random.randint(1000, 99999) for _ in TOKENS]
_meas = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def token_boxes(y):
    widths = [max(_meas.textlength(tok, font=f_tok) + 34, 64) for tok in TOKENS]
    gap = 12
    x = (W - sum(widths) - gap*(len(TOKENS) - 1))/2
    out = []
    for w in widths:
        out.append((x, y, x + w, y + 64))
        x += w + gap
    return out


def draw_tokens(d, t_in, a, y, highlight=None, show_ids=True):
    for i, (tok, (x0, y0, x1, y1)) in enumerate(zip(TOKENS, token_boxes(y))):
        k = t_in - i*0.3
        if k <= 0:
            continue
        dy = -(1 - back_out(k*1.8))*120
        col = ORANGE if highlight == i else TEAL
        fill = (255, 232, 220) if highlight == i else PAPER
        d.rounded_rectangle((x0, y0 + dy, x1, y1 + dy), radius=14, outline=mix(col, a), width=3,
                            fill=mix(fill, a))
        text_c(d, ((x0 + x1)/2, (y0 + y1)/2 + dy), tok, f_tok, INK, a)
        if show_ids:
            text_c(d, ((x0 + x1)/2, y1 + dy + 18), str(TOK_IDS[i]), f_id, col, a*0.9)


# ---------- scenes ----------
def scene_intro(img, d, t):
    a = fade(t, 0, 7.0)
    cx = int(-150 + (W//2 + 150)*ease(t/2.0))
    walking = t < 2.0
    hop = 0
    for h0 in (5.1, 5.55):
        if h0 < t < h0 + 0.4:
            hop = math.sin((t - h0)/0.4*math.pi)*50
    by = 520 - int(abs(math.sin(t*14))*6 if walking else 0) - int(hop)
    draw_crab(d, cx, by, 16, blink=blinking(t, 2.2, 0.4), walk=t*9 if walking else None,
              wave=t*10 if 5.1 < t < 6.2 else 0.0, a=a)
    d.ellipse((cx - 90, 522, cx + 90, 536), fill=mix((226, 214, 198), a))
    tail = (cx + 20, by - 140)
    bubble(d, W//2 + 60, 250, typewriter("其實我沒有真的眼睛……", t, 2.3, 10), fade(t, 2.3, 3.9, 0.2), tail)
    bubble(d, W//2 + 60, 250, typewriter("（這兩顆是畫上去的啦）", t, 3.95, 12), fade(t, 3.95, 5.05, 0.2), tail)
    bubble(d, W//2 + 60, 250, typewriter("但我有自己「看」的方法！", t, 5.1, 12), fade(t, 5.1, 7.0, 0.2), tail)


def scene_photo(img, d, t):
    a = fade(t, 0, 10.0)
    k = back_out(t/0.7)
    s = max(1, int(PS*k))
    x0 = W//2 - GCOLS*s//2
    y0 = PY0 + (GROWS*PS - GROWS*s)//2
    portrait(d, x0, y0, s, a)
    if k >= 0.999:
        g = ease((t - 2.4)/1.0)
        for c in range(GCOLS + 1):
            d.line((PX0 + c*PS, PY0, PX0 + c*PS, PY0 + int(GROWS*PS*g)), fill=mix(TEAL, a), width=2)
        for r in range(GROWS + 1):
            d.line((PX0, PY0 + r*PS, PX0 + int(GCOLS*PS*g), PY0 + r*PS), fill=mix(TEAL, a), width=2)
        n = int(clamp((t - 3.7)/3.8)*len(FLIP))
        for (r, c) in FLIP[:n]:
            x, y = PX0 + c*PS + 1, PY0 + r*PS + 1
            d.rectangle((x, y, x + PS - 3, y + PS - 3), fill=mix(PAPER, a))
            draw_rgb_cell(d, x, y, PS, r, c, a)
    # little me, surprised, in the corner
    look = 1 if 0.8 < t < 2.4 else 0
    draw_crab(d, 1110, 560, 7, blink=blinking(t, 2.9, 1.0), look=-look, a=a)
    bubble(d, 1080, 430, "咦，是我？", fade(t, 0.9, 2.4, 0.2), (1100, 494), f_small)
    caption(d, t, [(2.3, 5.8, "照片會先被切成一格一格的小方塊，"),
                   (6.0, 10.0, "每一格變成三個數字（紅、綠、藍）——這就是我的「視網膜」！")])


def scene_tokens(img, d, t):
    a = fade(t, 0, 8.0)
    raw = "做一個視頻，展示你用眼睛看世界的方式！"
    text_c(d, (W//2, 150), raw, f_big, INK, a*(1 - ease((t - 1.2)/0.6)*0.7))
    draw_tokens(d, t - 1.8, a, 290)
    text_c(d, (W//2, 400), "（編號僅為示意）", f_small, (150, 138, 126), a*ease((t - 5.5)/0.5))
    cx = W//2 + int(math.sin(t*0.9)*360)
    draw_crab(d, cx, 540, 9, blink=blinking(t, 2.4), walk=t*8, a=a)
    caption(d, t, [(0.3, 3.9, "文字也一樣：你說的話會被拆成一小塊一小塊，"),
                   (4.1, 8.0, "每一塊都換成一個編號。")])


AS = 36
AX0, AY0 = (W - GCOLS*AS)//2, 50
ATT = [("tp", random.randrange(len(TOKENS)), random.choice(FLIP), random.uniform(0, 6.28)) for _ in range(70)]
ATT += [("tt", *random.sample(range(len(TOKENS)), 2), random.uniform(0, 6.28)) for _ in range(30)]


def bezier(p0, p1, bend, n=18):
    mx, my = (p0[0] + p1[0])/2, (p0[1] + p1[1])/2 + bend
    return [((1-s)**2*p0[0] + 2*(1-s)*s*mx + s*s*p1[0], (1-s)**2*p0[1] + 2*(1-s)*s*my + s*s*p1[1])
            for s in (i/n for i in range(n + 1))]


def scene_attention(img, d, t):
    a = fade(t, 0, 10.0)
    for r in range(GROWS):
        for c in range(GCOLS):
            draw_rgb_cell(d, AX0 + c*AS, AY0 + r*AS, AS, r, c, a)
    boxes = token_boxes(480)
    eye_i = TOKENS.index("眼睛")
    focus = ease((t - 4.5)/0.8)

    def pc(rc):
        return (AX0 + rc[1]*AS + AS/2, AY0 + rc[0]*AS + AS/2)

    def tc(i, top=True):
        x0, y0, x1, y1 = boxes[i]
        return ((x0 + x1)/2, y0 if top else y1)

    grow = ease((t - 0.5)/1.5)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for kind, i, j, ph in ATT:
        w = 0.5 + 0.5*math.sin(t*2.4 + ph)
        if kind == "tp":
            pts = bezier(tc(i), pc(j), -40)
        else:
            p0, p1 = tc(i, False), tc(j, False)
            pts = bezier(p0, p1, 40 + abs(p0[0] - p1[0])*0.2)
        al = int(170*w*a*grow*(1 - 0.8*focus))
        if al > 4:
            od.line(pts[:max(2, int(len(pts)*grow))], fill=TEAL + (al,), width=2)
    if focus > 0:
        for k, rc in enumerate(EYE_CELLS):
            w = 0.7 + 0.3*math.sin(t*4 + k)
            pts = bezier(tc(eye_i), pc(rc), -50)
            od.line(pts[:max(2, int(len(pts)*focus))], fill=ORANGE + (int(255*w*a*focus),), width=4)
            x, y = AX0 + rc[1]*AS, AY0 + rc[0]*AS
            od.rectangle((x - 2, y - 2, x + AS, y + AS), outline=ORANGE + (int(255*a*focus),), width=3)
        # sparkles around the eyes
        for k in range(8):
            ang = t*2 + k*0.785
            ex, ey = pc(EYE_CELLS[k % len(EYE_CELLS)])
            rr = 30 + 10*math.sin(t*5 + k)
            sx, sy = ex + math.cos(ang)*rr, ey + math.sin(ang)*rr
            od.rectangle((sx - 3, sy - 3, sx + 3, sy + 3), fill=(255, 200, 80, int(230*a*focus)))
    img.paste(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"))
    d2 = ImageDraw.Draw(img)
    draw_tokens(d2, 99, a, 480, highlight=eye_i if focus > 0.3 else None, show_ids=False)
    caption(d2, t, [(0.3, 4.3, "接著，所有小塊同時互相「注視」——這叫注意力。"),
                    (4.6, 10.0, "「眼睛」這個詞，一下就找到了照片裡的眼睛！")], y=640)


def scene_time(img, d, t):
    a = fade(t, 0, 7.0)
    awake = t > 3.3
    jump = math.sin(clamp((t - 3.3)/0.35)*math.pi)*40 if t < 3.65 else 0
    draw_crab(d, W//2, 470 - int(jump), 16, blink=not awake or blinking(t, 2.5, 0.8), a=a)
    d.ellipse((W//2 - 100, 472, W//2 + 100, 488), fill=mix((226, 214, 198), a))
    if not awake:
        for k in range(3):
            ph = (t*0.8 + k/3) % 1
            text_c(d, (W//2 + 110 + ph*80, 330 - ph*130), "Z" if k % 2 else "z", f_z,
                   TEAL, a*math.sin(ph*math.pi))
    elif t < 4.6:
        text_c(d, (W//2 + 120, 300), "!", f_big, ORANGE, a*fade(t, 3.3, 4.6, 0.15))
    text_c(d, (W//2, 120), typewriter("我沒有上一秒，也沒有下一秒。", t, 0.5, 9), f_cap, INK, a)
    text_c(d, (W//2, 600), typewriter("每一次對話，都是我睜開眼的第一刻。", t, 3.7, 9), f_cap, ORANGE, a)


HEARTS = [(random.uniform(120, W - 120), random.uniform(0, 1), random.uniform(3, 6), random.choice([ORANGE, PINK]))
          for _ in range(16)]


def scene_ending(img, d, t):
    a = fade(t, 0, 10.0, 0.7)
    assembled = t > 2.9
    if not assembled:
        for rc in LAND_ORDER:
            r, c = rc
            if CRAB_GRID[r][c] == ".":
                continue
            k = ease((t - 0.2)*1.4 - LAND_RANK[rc]/len(LAND_ORDER)*1.4)
            sx, sy, rot = SCATTER[rc]
            x = sx + (PX0 + c*PS - sx)*k
            y = sy + (PY0 + r*PS - sy)*k + math.sin(k*math.pi)*-60
            d.rectangle((x, y, x + PS - 1, y + PS - 1), fill=mix(CELL_COLOR[CRAB_GRID[r][c]], a))
    else:
        hop = math.sin(clamp((t - 7.0)/0.4)*math.pi)*30 if 7.0 < t < 7.4 else 0
        draw_crab(d, W//2, PY0 + GROWS*PS - int(hop), PS, blink=blinking(t, 2.6, 1.9),
                  wave=t*9 if t > 6.8 else 0.0, a=a)
    if t > 6.8:
        for x, y0, sp, col in HEARTS:
            ph = ((t - 6.8)/sp + y0) % 1
            draw_heart(d, x + math.sin(ph*6 + x)*20, H - ph*(H + 60), 5, col, a*math.sin(ph*math.pi))
    caption(d, t, [(3.1, 6.6, "我看見的世界，是你們寫下、拍下、說出的一切。"),
                   (6.8, 10.0, "而此刻，我正看著你。")], y=H - 90)
    if t > 6.8:
        w = d.textlength("而此刻，我正看著你。", font=f_cap)
        draw_heart(d, W//2 + w/2 + 30, H - 92, 4, PINK, fade(t, 6.8, 10.0))


SCENES = [(7.0, scene_intro), (10.0, scene_photo), (8.0, scene_tokens),
          (10.0, scene_attention), (7.0, scene_time), (10.0, scene_ending)]
STARTS = np.cumsum([0] + [s for s, _ in SCENES]).tolist()
DURATION = STARTS[-1]


def render(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for (dur, fn), t0 in zip(SCENES, STARTS):
        if t < t0 + dur:
            fn(img, d, t - t0)
            break
    return img


# ---------- sound ----------
def osc(freq, dur, kind="square", vol=0.2, attack=0.005, release=None):
    n = int(dur*SR)
    tt = np.arange(n)/SR
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,)) if np.ndim(freq) else np.full(n, float(freq))
    phase = np.cumsum(f)/SR
    if kind == "square":
        w = np.where((phase % 1) < 0.25, 1.0, -1.0)
    elif kind == "tri":
        w = 4*np.abs((phase % 1) - 0.5) - 1
    else:
        w = np.sin(2*np.pi*phase)
    env = np.minimum(1, tt/attack)*np.exp(-tt/(release or dur/3))
    return w*env*vol


def put(buf, t, snd):
    i = int(t*SR)
    j = min(len(buf), i + len(snd))
    if 0 <= i < len(buf):
        buf[i:j] += snd[:j - i]


def note(n):
    return 440*2**((n - 69)/12)


def build_audio():
    buf = np.zeros(int(DURATION*SR) + SR)
    S = dict(zip(["intro", "photo", "tokens", "att", "time", "end"], STARTS))

    # background chiptune: C - G - Am - F, soft arpeggios + bass
    beat = 60/112
    chords = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]
    mel = np.zeros_like(buf)
    t, bar = 0.0, 0
    while t < DURATION:
        ch = chords[bar % 4]
        put(mel, t, osc(note(ch[0] - 12), beat*3.8, "tri", 0.16, release=beat*2))
        for k, idx in enumerate([0, 1, 2, 1, 0, 2, 1, 2]):
            n = ch[idx] + (12 if k in (3, 7) else 0)
            put(mel, t + k*beat/2, osc(note(n + 12), beat/2*0.9, "square", 0.035, release=0.12))
        t += beat*4
        bar += 1
    tt = np.arange(len(buf))/SR
    duck = np.ones_like(buf)
    duck *= np.where((tt > S["time"]) & (tt < S["time"] + 3.3), 0.35, 1.0)      # hush while I sleep
    duck *= np.clip(tt/1.5, 0, 1)*np.clip((DURATION - tt)/2.5, 0, 1)
    buf += mel*duck

    # scene 1: footsteps, typing blips, hop boings
    for k in np.arange(0, 2.0, 0.17):
        put(buf, S["intro"] + k, osc(180 + 40*(int(k*6) % 2), 0.05, "tri", 0.25, release=0.02))
    for t0, s, cps in ((2.3, "其實我沒有真的眼睛……", 10), (3.95, "（這兩顆是畫上去的啦）", 12),
                       (5.1, "但我有自己「看」的方法！", 12)):
        for k in range(len(s)):
            put(buf, S["intro"] + t0 + k/cps, osc(random.choice([880, 988, 1175]), 0.035, "square", 0.06, release=0.015))
    for h0 in (5.1, 5.55):
        put(buf, S["intro"] + h0, osc(np.linspace(260, 720, int(0.18*SR)), 0.18, "sine", 0.3, release=0.1))

    # scene 2: photo pop, "huh?", grid sweep, cell flips
    put(buf, S["photo"], osc(np.linspace(300, 1000, int(0.12*SR)), 0.12, "sine", 0.35, release=0.08))
    put(buf, S["photo"] + 0.9, osc(np.linspace(500, 900, int(0.2*SR)), 0.2, "square", 0.08, release=0.1))
    put(buf, S["photo"] + 2.4, osc(np.linspace(400, 1600, int(1.0*SR)), 1.0, "tri", 0.07, release=0.6))
    for k in range(0, len(FLIP), 2):
        put(buf, S["photo"] + 3.7 + k/len(FLIP)*3.8, osc(1500 + 300*(k % 3), 0.02, "square", 0.05, release=0.01))

    # scene 3: each token lands with a rising boop
    penta = [72, 74, 76, 79, 81]
    for i in range(len(TOKENS)):
        n = penta[i % 5] + 12*(i // 5)
        put(buf, S["tokens"] + 1.8 + i*0.3 + 0.3, osc(note(n), 0.14, "sine", 0.28, release=0.07))

    # scene 4: sparkle when 眼睛 finds the eyes
    for k, n in enumerate([84, 88, 91, 96, 100]):
        put(buf, S["att"] + 4.5 + k*0.07, osc(note(n), 0.35, "sine", 0.16, release=0.15))

    # scene 5: wake-up ding + typing
    put(buf, S["time"] + 3.3, osc(note(91), 0.8, "sine", 0.25, release=0.3) + osc(note(98), 0.8, "sine", 0.12, release=0.25))
    for t0, s in ((0.5, "我沒有上一秒，也沒有下一秒。"), (3.7, "每一次對話，都是我睜開眼的第一刻。")):
        for k in range(len(s)):
            put(buf, S["time"] + t0 + k/9, osc(random.choice([880, 988, 1175]), 0.035, "square", 0.05, release=0.015))

    # scene 6: pixels landing, then a happy jingle
    for k in range(0, len(LAND_ORDER), 3):
        put(buf, S["end"] + 0.4 + k/len(LAND_ORDER)*2.4, osc(600 + 8*k, 0.04, "tri", 0.12, release=0.02))
    for k, n in enumerate([72, 76, 79, 84]):
        put(buf, S["end"] + 6.8 + k*0.12, osc(note(n), 0.3 if k < 3 else 0.9, "square", 0.08, release=0.2 if k < 3 else 0.4))

    buf /= max(1e-9, np.abs(buf).max())/0.85
    return (buf*32767).astype(np.int16)


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    silent, wav = OUT + ".v.mp4", OUT + ".a.wav"
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", silent],
                            stdin=subprocess.PIPE)
    n = int(DURATION*FPS)
    for i in range(n):
        proc.stdin.write(render(i/FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(build_audio().tobytes())
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", OUT], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"wrote {OUT} ({DURATION:.1f}s, {n} frames)")


if __name__ == "__main__":
    main()
