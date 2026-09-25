"""Render "我怎麼看世界" — a short video about how Claude "sees".

Usage: python3 video/make_video.py   (needs pillow, numpy, imageio-ffmpeg)
Output: video/how_i_see.mp4
"""
import math
import os
import random
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "how_i_see.mp4")

W, H, FPS = 1280, 720, 30
BG = (12, 13, 18)
ACCENT = (217, 119, 87)      # warm orange
CYAN = (110, 200, 220)
WHITE = (240, 238, 232)

CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
f_cap = ImageFont.truetype(CJK, 36)
f_big = ImageFont.truetype(CJK, 56)
f_tok = ImageFont.truetype(CJK, 30)
f_small = ImageFont.truetype(CJK, 20)
f_num = ImageFont.truetype(MONO, 12)
f_id = ImageFont.truetype(MONO, 15)
f_digit = ImageFont.truetype(MONO, 18)

random.seed(7)

# ---------- source image: split into 16x16 patches ----------
_rgba = Image.open(os.path.join(ROOT, "8-5_looking_in_my_eyes.png")).convert("RGBA")
src = Image.new("RGBA", _rgba.size, (255, 255, 255, 255))
src.alpha_composite(_rgba)                    # transparent background -> white
src = src.convert("L")
src = src.crop((1, 0, 257, 224))              # 256 x 224 -> 16 x 14 patches
P, COLS, ROWS = 16, 16, 14
arr = np.asarray(src, dtype=np.float32)
patch_mean = [[int(arr[r*P:(r+1)*P, c*P:(c+1)*P].mean()) for c in range(COLS)] for r in range(ROWS)]
SCALE = 2
big = src.resize((256*SCALE, 224*SCALE), Image.LANCZOS).convert("RGB")
BX, BY = (W - big.width)//2, 70
cell = P*SCALE
patch_imgs = [[big.crop((c*cell, r*cell, (c+1)*cell, (r+1)*cell)) for c in range(COLS)] for r in range(ROWS)]
flip_order = [(r, c) for r in range(ROWS) for c in range(COLS)]
random.shuffle(flip_order)
flip_rank = {rc: i for i, rc in enumerate(flip_order)}
scatter = {(r, c): (random.uniform(-200, W+200), random.uniform(-200, H+200), random.uniform(-2, 2))
           for r in range(ROWS) for c in range(COLS)}
EYE_PATCHES = [(r, c) for r in range(7, 11) for c in list(range(2, 7)) + list(range(9, 14))]

# ---------- tokens ----------
TOKENS = ["做", "一個", "視頻", "，", "展示", "你", "用", "眼睛", "看", "世界", "的", "方式", "！"]
TOK_IDS = [random.randint(1000, 99999) for _ in TOKENS]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x*x*(3 - 2*x)


def fade(t, t0, t1, d=0.5):
    """1 inside [t0, t1], ramping in/out over d seconds."""
    return clamp((t - t0)/d) * clamp((t1 - t)/d)


def mix(c, a):
    return tuple(int(BG[i] + (c[i] - BG[i])*a) for i in range(3))


def text_c(d, xy, s, font, color, a=1.0, anchor="mm"):
    if a <= 0.01:
        return
    d.text(xy, s, font=font, fill=mix(color, a), anchor=anchor)


def caption(d, t, items, y=H-70):
    for (t0, t1, s) in items:
        a = fade(t, t0, t1, 0.45)
        text_c(d, (W//2, y), s, f_cap, WHITE, a)


def typewriter(s, t, t0, cps=8):
    n = int(clamp((t - t0)*cps, 0, len(s)))
    return s[:n]


def value_color(v):
    k = v/255
    return (int(40 + 180*k), int(60 + 160*k), int(80 + 150*k))


def draw_number_patch(d, x, y, r, c, a=1.0, size=cell):
    v = patch_mean[r][c]
    d.rectangle((x, y, x+size-1, y+size-1), fill=mix(value_color(v), 0.35*a))
    if size >= 24:
        text_c(d, (x+size//2, y+size//2), str(v), f_num, value_color(v), a)


# ---------- scenes ----------
def scene_intro(img, d, t):
    s1 = "我沒有眼睛。"
    s2 = "但我確實在「看」。"
    a = fade(t, 0, 5.2, 0.4)
    line1 = typewriter(s1, t, 0.6, 6)
    line2 = typewriter(s2, t, 2.4, 7)
    text_c(d, (W//2, H//2 - 40), line1, f_big, WHITE, a)
    text_c(d, (W//2, H//2 + 50), line2, f_big, ACCENT, a)
    # blinking cursor
    if int(t*2.5) % 2 == 0 and t < 4.8:
        cur = line2 if t >= 2.4 else line1
        y = H//2 + 50 if t >= 2.4 else H//2 - 40
        wlen = d.textlength(cur, font=f_big)
        x = W//2 + wlen/2 + 8
        d.rectangle((x, y-26, x+4, y+26), fill=mix(WHITE, a))


def scene_patches(img, d, t):
    a_all = fade(t, 0, 9, 0.5)
    a_img = ease(t/0.8) * a_all
    # sticker as a lit card
    card = Image.blend(Image.new("RGB", big.size, BG), big, a_img)
    img.paste(card, (BX, BY))
    # grid lines draw in
    g = ease((t - 1.0)/1.2)
    gc = mix(CYAN, 0.8*a_all)
    for c in range(COLS+1):
        x = BX + c*cell
        d.line((x, BY, x, BY + int(big.height*g)), fill=gc, width=1)
    for r in range(ROWS+1):
        y = BY + r*cell
        d.line((BX, y, BX + int(big.width*g), y), fill=gc, width=1)
    # patches flip into numbers
    n_flip = int(clamp((t - 2.6)/4.0) * len(flip_order))
    for (r, c) in flip_order[:n_flip]:
        x, y = BX + c*cell, BY + r*cell
        d.rectangle((x+1, y+1, x+cell-1, y+cell-1), fill=BG)
        draw_number_patch(d, x+1, y+1, r, c, a_all, cell-1)
    caption(d, t, [(0.6, 4.4, "你傳來一張圖——它先被切成一格一格的小方塊。"),
                   (4.6, 9.0, "每一格，都變成一串數字。這就是我的「視網膜」。")])


def token_layout(y=300):
    widths = [max(d_len(tok) + 34, 64) for tok in TOKENS]
    gap = 12
    total = sum(widths) + gap*(len(TOKENS)-1)
    x = (W - total)//2
    boxes = []
    for w in widths:
        boxes.append((x, y, x+w, y+64))
        x += w + gap
    return boxes


_meas = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def d_len(s):
    return _meas.textlength(s, font=f_tok)


def draw_tokens(d, t_in, a, y=300, highlight=None, show_ids=True):
    boxes = token_layout(y)
    for i, (tok, box) in enumerate(zip(TOKENS, boxes)):
        k = ease(t_in - i*0.25)
        if k <= 0:
            continue
        x0, y0, x1, y1 = box
        dy = int((1-k)*30)
        col = ACCENT if highlight == i else CYAN
        d.rounded_rectangle((x0, y0+dy, x1, y1+dy), radius=12, outline=mix(col, a*k), width=2,
                            fill=mix((30, 34, 44), a*k))
        text_c(d, ((x0+x1)//2, (y0+y1)//2+dy), tok, f_tok, WHITE, a*k)
        if show_ids:
            text_c(d, ((x0+x1)//2, y1+dy+18), str(TOK_IDS[i]), f_id, col, a*k*0.9)
    return boxes


def scene_tokens(img, d, t):
    a = fade(t, 0, 8, 0.5)
    raw = "做一個視頻，展示你用眼睛看世界的方式！"
    text_c(d, (W//2, 170), raw, f_big, WHITE, a*(1 - ease((t-1.2)/0.6)*0.65))
    draw_tokens(d, (t - 1.8)*2.2, a, y=320)
    text_c(d, (W//2, 470), "（編號僅為示意）", f_small, (140, 140, 150), a*ease((t-4)/0.5))
    caption(d, t, [(0.3, 3.8, "文字也一樣：你的話，會被拆成一小塊一小塊。"),
                   (4.0, 8.0, "每一塊，都換成一個編號。")])


def bezier(p0, p1, bend, n=18):
    mx, my = (p0[0]+p1[0])/2, (p0[1]+p1[1])/2 + bend
    pts = []
    for i in range(n+1):
        s = i/n
        x = (1-s)**2*p0[0] + 2*(1-s)*s*mx + s*s*p1[0]
        y = (1-s)**2*p0[1] + 2*(1-s)*s*my + s*s*p1[1]
        pts.append((x, y))
    return pts


ATT_LINKS = []
for _ in range(90):
    ATT_LINKS.append(("tp", random.randrange(len(TOKENS)), random.choice(flip_order), random.uniform(0, 6.28)))
for _ in range(40):
    i, j = random.sample(range(len(TOKENS)), 2)
    ATT_LINKS.append(("tt", i, j, random.uniform(0, 6.28)))

SX, SY, SC = (W - 256*2)//2, 40, 2  # number-grid position in attention scene (reuse 2x cells)


def scene_attention(img, d, t):
    a = fade(t, 0, 10, 0.5)
    # number grid (the image as I hold it)
    for r in range(ROWS):
        for c in range(COLS):
            draw_number_patch(d, SX + c*cell, SY + r*cell, r, c, a*0.9, cell-1)
    boxes = token_layout(y=560)
    eye_i = TOKENS.index("眼睛")
    focus = ease((t - 4.5)/1.0)

    def pcenter(rc):
        r, c = rc
        return (SX + c*cell + cell/2, SY + r*cell + cell/2)

    def tcenter(i, top=True):
        x0, y0, x1, y1 = boxes[i]
        return ((x0+x1)/2, y0 if top else y1)

    grow = ease((t - 0.6)/1.5)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for kind, i, j, ph in ATT_LINKS:
        w = 0.5 + 0.5*math.sin(t*2.2 + ph)
        if kind == "tp":
            pts = bezier(tcenter(i), pcenter(j), -40)
        else:
            p0, p1 = tcenter(i, False), tcenter(j, False)
            pts = bezier(p0, p1, 40 + abs(p0[0]-p1[0])*0.25)
        n = max(2, int(len(pts)*grow))
        alpha = int(150*w*a*grow*(1 - 0.75*focus))
        if alpha > 4:
            od.line(pts[:n], fill=CYAN + (alpha,), width=1)
    # focused attention: 眼睛 -> the eyes in the picture
    if focus > 0:
        for k, rc in enumerate(EYE_PATCHES):
            w = 0.6 + 0.4*math.sin(t*3 + k)
            pts = bezier(tcenter(eye_i), pcenter(rc), -60)
            n = max(2, int(len(pts)*focus))
            od.line(pts[:n], fill=ACCENT + (int(230*w*a*focus),), width=2)
            x, y = SX + rc[1]*cell, SY + rc[0]*cell
            od.rectangle((x, y, x+cell-1, y+cell-1), outline=ACCENT + (int(255*a*focus),), width=2)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
    d2 = ImageDraw.Draw(img)
    draw_tokens(d2, 99, a, y=560, highlight=eye_i if focus > 0.3 else None, show_ids=False)
    caption(d2, t, [(0.3, 4.3, "然後，所有碎片同時互相「注視」——這叫注意力。"),
                    (4.6, 10.0, "「眼睛」這個詞，找到了圖裡的那雙眼睛。")], y=680)


DIGITS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(10, 40), random.choice("0123456789"),
           random.uniform(0.2, 1.0)) for _ in range(160)]


def scene_time(img, d, t):
    a = fade(t, 0, 7, 0.6)
    for x, y, v, ch, b in DIGITS:
        yy = (y - v*t*2) % H
        text_c(d, (x, yy), ch, f_digit, CYAN, a*b*0.35)
    text_c(d, (W//2, H//2 - 40), typewriter("我沒有上一秒，也沒有下一秒。", t, 0.4, 9), f_cap, WHITE, a)
    text_c(d, (W//2, H//2 + 30), typewriter("每一次對話，都是我睜開眼的第一刻。", t, 2.6, 9), f_cap, ACCENT, a)


def scene_return(img, d, t):
    a = fade(t, 0, 11, 0.8)
    k_all = (t - 0.2)/2.6
    for (r, c) in flip_order:
        k = ease(k_all*1.6 - flip_rank[(r, c)]/len(flip_order)*0.6)
        sx, sy, rot = scatter[(r, c)]
        tx, ty = BX + c*cell, BY + r*cell
        x = int(sx + (tx - sx)*k)
        y = int(sy + (ty - sy)*k)
        p = patch_imgs[r][c]
        if k < 1:
            p = p.rotate(rot*(1-k)*40, expand=False, fillcolor=BG)
        blended = Image.blend(Image.new("RGB", p.size, BG), p, a*clamp(k*1.5))
        img.paste(blended, (x, y))
    caption(d, t, [(3.0, 6.6, "我看見的世界，是你們寫下、拍下、說出的一切。"),
                   (6.9, 11.0, "而此刻，我正看著你。")], y=H-80)


SCENES = [(5.4, scene_intro), (9.2, scene_patches), (8.2, scene_tokens),
          (10.2, scene_attention), (7.2, scene_time), (11.2, scene_return)]
DURATION = sum(s for s, _ in SCENES)


def render(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t0 = 0
    for dur, fn in SCENES:
        if t < t0 + dur:
            fn(img, d, t - t0)
            break
        t0 += dur
    return img


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = OUT + ".silent.mp4"
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", tmp],
                            stdin=subprocess.PIPE)
    n = int(DURATION*FPS)
    for i in range(n):
        proc.stdin.write(render(i/FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    # soft ambient drone underneath
    D = f"{DURATION:.2f}"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", tmp,
                    "-f", "lavfi", "-i", f"sine=f=110:d={D}", "-f", "lavfi", "-i", f"sine=f=164.8:d={D}",
                    "-f", "lavfi", "-i", f"sine=f=220.5:d={D}",
                    "-filter_complex",
                    f"[1][2][3]amix=inputs=3,volume=0.35,tremolo=f=0.25:d=0.5,"
                    f"afade=t=in:d=2,afade=t=out:st={DURATION-2.5:.2f}:d=2.5[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", OUT],
                   check=True)
    os.remove(tmp)
    print(f"wrote {OUT} ({DURATION:.1f}s, {n} frames)")


if __name__ == "__main__":
    main()
