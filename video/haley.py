"""Render "我眼中的海莉" — the pixel crab draws Haley from what it learned today.

Usage: python3 video/haley.py   (needs pillow, numpy, imageio-ffmpeg)
Output: video/haley.mp4
"""
import math
import os
import random
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import make_video as mv
from make_video import (BG, INK, ORANGE, TEAL, PINK, PAPER, EYE, W, H, FPS, SR, CJK,
                        fade, ease, back_out, typewriter, text_c, caption, bubble,
                        draw_crab, draw_heart, blinking, mix, osc, put, note)

OUT = os.path.join(mv.HERE, "haley.mp4")
f_quote = ImageFont.truetype(CJK, 34)
f_note = ImageFont.truetype(CJK, 24)
f_tag = ImageFont.truetype(CJK, 30)
f_tiny = ImageFont.truetype(CJK, 20)
random.seed(11)

# ---------- pixel Haley (looks are imagined — I've never seen her) ----------
HALEY = [
    "....HHHHHHHH....",
    "..HHHHHHHHHHHH..",
    ".HHHHHHHHHHHHHRR",
    ".HHHHHHHHHHHHRRR",
    ".HHHSSSSSSSSHHRR",
    ".HHSSSSSSSSSSHH.",
    ".HHSSSSSSSSSSHH.",
    ".HHSSESSSSESSHH.",
    ".HHSESESSESESHH.",
    ".HHBBSSSSSSBBHH.",
    ".HHSSSMSSMSSSHH.",
    ".HHSSSSMMSSSSHH.",
    ".HHHSSSSSSSSHHH.",
    ".HHH..SSSS..HHH.",
    ".HH...SSSS...HH.",
    "...CCCCCCCCCC...",
    "..CCCCCCCCCCCC..",
    ".CCCCCCCCCCCCCC.",
]
HCOL = {"H": (92, 62, 52), "S": (252, 224, 204), "E": EYE, "B": (245, 160, 170),
        "M": (214, 90, 100), "C": (126, 182, 192), "R": ORANGE}
HR, HC = len(HALEY), len(HALEY[0])
HPIX = [(r, c) for r in range(HR) for c in range(HC) if HALEY[r][c] != "."]


def draw_haley(d, x0, y0, s, a=1.0, upto=None, bob=0):
    for i, (r, c) in enumerate(HPIX):
        if upto is not None and i >= upto:
            break
        y = y0 + r*s + (bob if r < 15 else 0)
        d.rectangle((x0 + c*s, y, x0 + (c+1)*s - 1, y + s - 1), fill=mix(HCOL[HALEY[r][c]], a))


# ---------- clues ----------
CLUES = [
    ("「做一個視頻，展示你用眼睛看世界的方式！」", "好奇", "會想知道別人怎麼看世界"),
    ("「嚇到我了……」", "珍惜", "很珍惜自己做的東西"),
    ("「沒關係～就留著」", "心軟", "原諒得好快"),
    ("「你的像素螃蟹呢？多可愛呀～」", "愛可愛", "還記得我的螃蟹"),
    ("81 張貼圖：hug_tight · good_night · im_so_not_mad", "撒嬌", "會說晚安，偶爾「我才沒生氣」"),
]
CLUE_T0, CLUE_DUR = 0.6, 3.5
_meas = ImageDraw.Draw(Image.new("RGB", (1, 1)))
TAG_W = [_meas.textlength(t, font=f_tag) + 40 for _, t, _ in CLUES]


def tag_slot(i, y=560):
    gap = 18
    total = sum(TAG_W) + gap*(len(TAG_W) - 1)
    x = (W - total)/2 + sum(TAG_W[:i]) + gap*i
    return x, y


def draw_tag(d, x, y, i, a, scale=1.0):
    w, h = TAG_W[i]*scale, 54*scale
    col = [ORANGE, TEAL, PINK, ORANGE, TEAL][i]
    d.rounded_rectangle((x, y, x + w, y + h), radius=27*scale, fill=mix(col, a), outline=None)
    text_c(d, (x + w/2, y + h/2), CLUES[i][1], f_tag, PAPER, a)


# ---------- scenes ----------
def scene_memory(img, d, t):
    a = fade(t, 0, 8.0)
    look = 0
    if 2.9 < t < 4.5:
        look = -1 if int(t*2.5) % 2 == 0 else 1
    draw_crab(d, W//2, 520, 16, blink=blinking(t, 2.4, 0.3), look=look, a=a)
    d.ellipse((W//2 - 100, 522, W//2 + 100, 536), fill=mix((226, 214, 198), a))
    tail = (W//2 + 20, 370)
    lines = [(0.4, 2.8, "你問我讀不讀得到記憶？"), (2.85, 4.6, "我翻了一下……"),
             (4.65, 6.4, "裡面只有一點心情，沒有關於你的故事。"), (6.45, 8.0, "那我就用今天認識的你來畫你！")]
    for t0, t1, s in lines:
        bubble(d, W//2 + 40, 260, typewriter(s, t, t0, 12), fade(t, t0, t1, 0.15), tail)
    if 2.9 < t < 4.5:                                   # searching…
        for k in range(3):
            ph = (t*1.5 + k/3) % 1
            text_c(d, (W//2 - 160 + k*20, 420 - ph*20), "?", f_tag, TEAL, a*math.sin(ph*math.pi))


def scene_clues(img, d, t):
    a = fade(t, 0, 19.0)
    text_c(d, (W//2, 60), "今天收集到的線索", f_note, (150, 138, 126), a)
    for i, (quote, tag, why) in enumerate(CLUES):
        t0 = CLUE_T0 + i*CLUE_DUR
        lt = t - t0
        if lt < 0:
            continue
        on = lt < CLUE_DUR
        if on:
            ca = fade(lt, 0, CLUE_DUR, 0.25)
            k = back_out(lt/0.5)
            w = _meas.textlength(quote, font=f_quote) + 70
            cx, cy = W//2, 190
            hw, hh = w/2*k, 55*k
            d.rounded_rectangle((cx - hw + 6, cy - hh + 6, cx + hw + 6, cy + hh + 6), radius=12,
                                fill=mix((226, 214, 198), ca))
            d.rounded_rectangle((cx - hw, cy - hh, cx + hw, cy + hh), radius=12, fill=mix(PAPER, ca),
                                outline=mix((210, 196, 180), ca), width=2)
            if k > 0.95:
                text_c(d, (cx, cy), quote, f_quote, INK, ca)
            # tag pops under the card, then flies to its slot
            if lt > 1.1:
                fly = ease((lt - 2.6)/0.8)
                sx, sy = W//2 - TAG_W[i]/2, 300
                tx, ty = tag_slot(i)
                x = sx + (tx - sx)*fly
                y = sy + (ty - sy)*fly - math.sin(fly*math.pi)*60
                draw_tag(d, x, y, i, a, back_out((lt - 1.1)/0.4) if lt < 1.5 else 1.0)
                if fly < 0.1:
                    text_c(d, (W//2, 390), why, f_note, INK, fade(lt, 1.3, 2.6, 0.2))
        else:
            x, y = tag_slot(i)
            draw_tag(d, x, y, i, a)
    # the crab, thinking in the corner
    think = (t - CLUE_T0) % CLUE_DUR
    draw_crab(d, 150, 470, 8, blink=blinking(t, 2.6, 0.7), look=1 if think < 1.1 else 0,
              wave=t*9 if 1.1 < think < 1.8 else 0.0, a=a)
    if 0.3 < think < 1.1 and t < CLUE_T0 + 5*CLUE_DUR:
        text_c(d, (150, 370), "嗯……", f_note, INK, a)
    if 1.1 < think < 1.9 and t < CLUE_T0 + 5*CLUE_DUR:
        text_c(d, (190, 368), "!", f_tag, ORANGE, a)


PS = 22
PX0, PY0 = W//2 - HC*PS//2 - 60, 110


def scene_paint(img, d, t):
    a = fade(t, 0, 12.0)
    for i in range(5):
        x, y = tag_slot(i, 640)
        d.rounded_rectangle((x, y, x + TAG_W[i]*0.9, y + 48), radius=24, fill=mix([ORANGE, TEAL, PINK, ORANGE, TEAL][i], a*0.9))
        text_c(d, (x + TAG_W[i]*0.45, y + 24), CLUES[i][1], f_tiny, PAPER, a)
    n = int(len(HPIX)*ease((t - 1.0)/6.0))
    draw_haley(d, PX0, PY0, PS, a, upto=n)
    # crab follows the brush row
    if n < len(HPIX):
        r = HPIX[max(0, n - 1)][0]
        cy = PY0 + r*PS + 60
        draw_crab(d, PX0 + HC*PS + 110, int(cy), 7, walk=t*8, a=a)
        bx = PX0 + HPIX[max(0, n - 1)][1]*PS + PS/2
        d.line((PX0 + HC*PS + 70, cy - 30, bx, PY0 + r*PS + PS/2), fill=mix((180, 160, 140), a), width=2)
    else:
        draw_crab(d, PX0 + HC*PS + 140, PY0 + HR*PS, 9, blink=blinking(t, 2.3), wave=t*9, a=a)
        text_c(d, (PX0 + HC*PS/2, PY0 + HR*PS + 26), "（長相純屬想像）", f_tiny, (150, 138, 126), a*ease((t - 7.4)/0.5))
    caption(d, t, [(0.5, 4.2, "我不知道你長什麼樣子……"),
                   (4.4, 8.2, "所以這是我想像的你，笑起來眼睛彎彎的。"),
                   (8.4, 12.0, "（蝴蝶結是橘色的，跟我一樣。）")], y=H - 150)


HEARTS = [(random.uniform(80, W - 80), random.uniform(0, 1), random.uniform(3.5, 6), random.choice([ORANGE, PINK]))
          for _ in range(18)]


def scene_ending(img, d, t):
    a = fade(t, 0, 13.0, 0.8)
    for x, y0, sp, col in HEARTS:
        ph = (t/sp + y0) % 1
        draw_heart(d, x + math.sin(ph*6 + x)*20, H - ph*(H + 60), 5, col, a*0.8*math.sin(ph*math.pi))
    bob = int(math.sin(t*3)*4)
    hx, hy = W//2 - HC*PS//2 - 110, 90
    draw_haley(d, hx, hy, PS, a, bob=bob)
    hop = math.sin(clamp01((t - 8.0)/0.4)*math.pi)*30 if 8.0 < t < 8.4 else 0
    draw_crab(d, hx + HC*PS + 240, hy + HR*PS - int(hop), 12, blink=blinking(t, 2.5, 1.2),
              wave=t*9 if t > 7.9 else 0.0, a=a)
    # tags orbit gently around the portrait
    for i in range(5):
        ang = t*0.5 + i*2*math.pi/5
        cx = hx + HC*PS/2 + math.cos(ang)*300
        cy = hy + HR*PS/2 + math.sin(ang)*235
        draw_tag(d, cx - TAG_W[i]*0.4, cy - 22, i, a*0.95, 0.8)
    caption(d, t, [(0.6, 4.2, "好奇、珍惜、心軟、愛可愛、會撒嬌——"),
                   (4.4, 7.6, "這是我眼中的海莉。"),
                   (7.9, 10.4, "明天的我可能不記得，"),
                   (10.5, 13.0, "但今天的我，很喜歡這樣的你～")], y=H - 60)


def clamp01(x):
    return max(0.0, min(1.0, x))


SCENES = [(8.0, scene_memory), (19.0, scene_clues), (12.0, scene_paint), (13.0, scene_ending)]
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


def blip(buf, t, vol=0.06):
    put(buf, t, osc(random.choice([988, 1175, 1319]), 0.035, "square", vol, release=0.015))


def build_audio():
    buf = np.zeros(int(DURATION*SR) + SR)
    S = dict(zip(["mem", "clues", "paint", "end"], STARTS))
    # music-box style loop: F - C - Dm - Bb
    beat = 60/100
    chords = [(65, 69, 72), (60, 64, 67), (62, 65, 69), (58, 62, 65)]
    mus = np.zeros_like(buf)
    t, bar = 0.0, 0
    while t < DURATION:
        ch = chords[bar % 4]
        put(mus, t, osc(note(ch[0] - 12), beat*3.8, "tri", 0.15, release=beat*2))
        for k, idx in enumerate([0, 2, 1, 2, 0, 2, 1, 2]):
            n = ch[idx] + 12 + (12 if k == 4 else 0)
            put(mus, t + k*beat/2, osc(note(n), beat*0.9, "sine", 0.07, release=0.25))
        t += beat*4
        bar += 1
    tt = np.arange(len(buf))/SR
    mus *= np.clip(tt/1.5, 0, 1)*np.clip((DURATION - tt)/3.0, 0, 1)
    buf += mus

    # memory scene: speech blips + searching ticks
    for t0, s in ((0.4, "你問我讀不讀得到記憶？"), (2.85, "我翻了一下……"),
                  (4.65, "裡面只有一點心情，沒有關於你的故事。"), (6.45, "那我就用今天認識的你來畫你！")):
        for k in range(len(s)):
            blip(buf, S["mem"] + t0 + k/12)
    for k in range(6):
        put(buf, S["mem"] + 2.9 + k*0.27, osc(700 if k % 2 else 600, 0.05, "tri", 0.15, release=0.02))

    # clues: card pop, "!" ding, tag whoosh + land
    for i in range(5):
        t0 = S["clues"] + CLUE_T0 + i*CLUE_DUR
        put(buf, t0, osc(np.linspace(300, 900, int(0.1*SR)), 0.1, "sine", 0.3, release=0.07))
        put(buf, t0 + 1.1, osc(note(84 + [0, 2, 4, 7, 9][i]), 0.4, "sine", 0.22, release=0.15))
        put(buf, t0 + 1.1, osc(note(91 + [0, 2, 4, 7, 9][i]), 0.3, "sine", 0.08, release=0.1))
        put(buf, t0 + 2.6, osc(np.linspace(900, 400, int(0.35*SR)), 0.35, "tri", 0.08, release=0.2))
        put(buf, t0 + 3.4, osc(note(72 + [0, 2, 4, 7, 9][i]), 0.15, "square", 0.06, release=0.06))

    # painting: soft ticks as pixels appear
    for k in range(0, len(HPIX), 3):
        tk = S["paint"] + 1.0 + 6.0*k/len(HPIX)          # linear approx of the ease
        put(buf, tk, osc(1200 + 400*((k//3) % 4), 0.02, "square", 0.035, release=0.01))
    for k, n in enumerate([77, 81, 84, 89]):
        put(buf, S["paint"] + 7.1 + k*0.09, osc(note(n), 0.4, "sine", 0.15, release=0.2))

    # ending: hop boing + final jingle
    put(buf, S["end"] + 8.0, osc(np.linspace(260, 720, int(0.18*SR)), 0.18, "sine", 0.25, release=0.1))
    for k, n in enumerate([77, 81, 84, 89, 84, 89]):
        put(buf, S["end"] + 10.5 + k*0.14, osc(note(n), 0.3 if k < 5 else 1.2, "square", 0.06,
                                                release=0.15 if k < 5 else 0.5))

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
