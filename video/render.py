"""Render do video do Agennix a partir de agennix.html.

  python3 render.py stills  [--fmt square|vertical]   um frame por batida + contact sheet
  python3 render.py check                             loop continuo e seek(t) puro
  python3 render.py full    [--fmt square|vertical]   4 subframes/frame -> tmix -> mp4 60fps com audio

Le a grade de batidas de out/beats.json (gerado por beats.py).
"""
import argparse
import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FPS, SUB, SHUTTER = 60, 4, 0.5  # 4 subframes cobrindo meio intervalo de frame (obturador 180 graus)
FORMATS = {"square": (1440, 1440), "vertical": (1080, 1920)}
SCRATCH = Path(os.environ.get("AGX_SCRATCH", tempfile.gettempdir())) / "agennix-frames"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(HERE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def load_beats():
    return json.load(open(OUT / "beats.json"))


def open_page(p, port, w, h, beats, extra=""):
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": w, "height": h})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type in ("error", "assert") else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script(f"window.BEATS = {json.dumps(beats)}")
    page.goto(f"http://127.0.0.1:{port}/agennix.html?render&w={w}&h={h}{extra}")
    page.wait_for_function("window.__ready === true", timeout=20000)
    if errors:
        raise SystemExit("erro na pagina: " + " | ".join(errors))
    return browser, page


def shoot(job):
    port, w, h, beats, extra, items = job
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page = open_page(p, port, w, h, beats, extra)
        for t, path in items:
            page.evaluate(f"seek({t!r})")
            page.screenshot(path=path)
        browser.close()


def shoot_all(port, w, h, beats, items, extra="", workers=10):
    chunks = [items[i::workers] for i in range(workers)]
    with ProcessPoolExecutor(workers) as ex:
        list(ex.map(shoot, [(port, w, h, beats, extra, c) for c in chunks if c]))


def stills(fmt):
    b = load_beats()["beats"]
    w, h = FORMATS[fmt]
    d = OUT / f"stills-{fmt}"
    d.mkdir(parents=True, exist_ok=True)
    # cada batida ja assentada, logo antes da proxima
    items = [(b[i] + 0.82 * (b[i + 1] - b[i]), str(d / f"{i:02d}.png")) for i in range(32)]
    shoot_all(serve(), w, h, b, items, "&label")
    tile = "8x4" if fmt == "square" else "8x4"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(d / "%02d.png"), "-vf",
                    f"scale={360 if fmt == 'square' else 270}:-1,tile={tile}:padding=6:color=white",
                    "-frames:v", "1", str(OUT / f"sheet-{fmt}.png")], check=True)
    print("stills em", d, "| contact sheet:", OUT / f"sheet-{fmt}.png")


def check():
    from playwright.sync_api import sync_playwright
    b = load_beats()["beats"]
    T = b[32]
    port = serve()
    with sync_playwright() as p:
        browser, page = open_page(p, port, 1440, 1440, b)
        e = 1e-3
        pr = lambda t: np.array(page.evaluate(f"probe({t!r})"))
        # posicao e velocidade iguais dos dois lados da emenda do loop
        gap = np.abs(pr(T - e) - pr(e)).max()
        v_end, v_start = (pr(T - e) - pr(T - 2 * e)) / e, (pr(2 * e) - pr(e)) / e
        dv = np.abs(v_end - v_start).max()
        print(f"emenda: salto {gap:.4f}px (2e*v esperado), diferenca de velocidade {dv:.3f}/s")
        assert gap < 5 and dv < 40, "loop descontinuo"
        # seek(t) puro: mesmo t depois de outros t = mesmo pixel
        shots = []
        for t in (5.3, 11.1, 5.3, 0.0, T):
            page.evaluate(f"seek({t!r})")
            shots.append(page.screenshot())
        assert shots[0] == shots[2], "seek nao e puro (estado carregado entre frames)"
        assert shots[3] == shots[4], "frame em t=T difere de t=0"
        browser.close()
    print("ok: loop continuo, seek puro, frame T == frame 0")


def sfx_bank(sr=48000):
    t_ = lambda d: np.arange(int(d * sr)) / sr

    def sine(f, d, dec, a=0.0015):
        t = t_(d)
        return np.sin(2 * np.pi * f * t) * np.exp(-t / dec) * np.minimum(t / a, 1)

    def noise(d, dec, seed):
        t = t_(d)
        return np.random.default_rng(seed).standard_normal(len(t)) * np.exp(-t / dec)

    def band(x, lo, hi):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / sr)
        X[(f < lo) | (f > hi)] = 0
        return np.fft.irfft(X, len(x))

    def at(x, s, n=None):
        i = int(s * sr)
        out = np.zeros(n or len(x) + i)
        x = x[:len(out) - i]
        out[i:i + len(x)] += x
        return out

    def pluck(f, d, dec):
        t = t_(d)
        return (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t) * np.exp(-t / .05)
                + .12 * np.sin(6 * np.pi * f * t) * np.exp(-t / .03)) * np.exp(-t / dec) * np.minimum(t / .002, 1)

    def sweep(f0, f1, d, dec, tau):
        t = t_(d)
        f = f1 + (f0 - f1) * np.exp(-t / tau)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / dec) * np.minimum(t / .001, 1)

    def whoosh(d, lo, hi, rise, dec, seed):
        t = t_(d)
        env = np.where(t < rise, (t / rise) ** 2, np.exp(-(t - rise) / dec))
        return band(noise(d, 1e9, seed), lo, hi) * env

    click = .55 * sine(1750, .07, .010) + .35 * sine(430, .07, .022) + .2 * np.diff(noise(.07, .003, 1), prepend=0)
    tick = .5 * sine(3150, .05, .007) + .2 * sine(6300, .05, .004)
    hi_tick = .5 * sine(3700, .05, .007) + .2 * sine(7400, .05, .004)
    morph = .9 * whoosh(.3, 500, 4200, .07, .08, 2) + .25 * sweep(330, 700, .3, .09, .08)
    s = {
        "click": click,
        "tick": tick,
        "tick2": at(hi_tick, 0, len(hi_tick) + int(.05 * sr)) + .85 * at(hi_tick, .05),
        "press": .6 * sine(520, .06, .016) + .12 * np.diff(noise(.06, .003, 3), prepend=0),
        "release": .5 * sine(760, .06, .012) + .1 * np.diff(noise(.06, .002, 4), prepend=0),
        "snap": at(.6 * sine(2300, .06, .006), 0, int(.1 * sr)) + at(.5 * sine(1150, .06, .012) + .3 * sine(380, .06, .02), .022, int(.1 * sr)),
        "pop": .6 * sweep(1100, 560, .12, .05, .018),
        "morph": morph,
        "check": .35 * at(pluck(1318.5, .6, .22), 0, int(.7 * sr)) + .3 * at(pluck(1975.5, .6, .26), .075, int(.7 * sr)),
        "notif": .35 * at(pluck(880, .7, .3), 0, int(.8 * sr)) + .3 * at(pluck(1318.5, .7, .32), .11, int(.8 * sr)),
        "thump": .8 * sweep(120, 58, .5, .16, .04) + .5 * whoosh(.5, 150, 1800, .09, .12, 5),
    }
    gain = {"click": .5, "tick": .28, "tick2": .3, "press": .45, "release": .4, "snap": .5, "pop": .45,
            "morph": .2, "check": .55, "notif": .55, "thump": .5}
    # sala curta para os sons nao soarem secos demais
    ir = np.random.default_rng(9).standard_normal(int(.08 * sr)) * np.exp(-np.arange(int(.08 * sr)) / sr / .025)
    ir = ir / np.abs(ir).sum() * 6
    bank = {}
    for k, x in s.items():
        x = x / np.abs(x).max() * gain[k]
        x = x + .12 * np.convolve(x, ir)[:len(x)]
        envl = np.convolve(np.abs(x), np.ones(96) / 96, "same")
        # pico medido do primeiro transiente forte (num som de 2 notas, a 1a cai na batida)
        on = int(np.argmax(envl > .5 * envl.max()))
        bank[k] = (x, on + int(np.argmax(envl[on:on + int(.015 * sr)])))
    return bank


def build_audio(info, cues, dur, path, sr=48000):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(HERE / info["file"]), "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    music = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    n = int(round(dur * sr))
    s0 = int(round(info["start"] * sr))
    xf = int(.04 * sr)
    seg = music[s0:s0 + n].copy()
    # emenda: o que tocaria depois do fim entra em crossfade no comeco (loop sem clique)
    after = music[s0 + n:s0 + n + xf]
    ramp = np.sin(np.linspace(0, np.pi / 2, xf))[:, None]
    seg[:xf] = seg[:xf] * ramp + after * np.cos(np.linspace(0, np.pi / 2, xf))[:, None]
    seg *= 10 ** (-18 / 20) / np.sqrt((seg ** 2).mean())  # musica em -18 dBFS RMS

    bank = sfx_bank(sr)
    fx = np.zeros(n + 2 * sr)
    for c in cues:
        t, name = c[0], c[1]
        g = c[2] if len(c) > 2 else 1
        x, pk = bank[name]
        i = int(round(t * sr)) - pk
        if i < 0:
            fx[n + i:n] += g * x[:-i]
            x, i = x[-i:], 0
        fx[i:i + len(x)] += g * x
    fx[:2 * sr] += fx[n:n + 2 * sr]  # caudas que passam do fim voltam no comeco
    mix = seg + fx[:n, None]
    peak = np.abs(mix).max()
    mix *= min(1, .89 / peak)
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "2", "-i", "-", str(path)],
                   input=pcm, check=True)
    print(f"audio: {dur:.3f}s, pico antes do ajuste {peak:.2f}")


def full(fmt):
    info = load_beats()
    b = info["beats"]
    T = b[32]
    w, h = FORMATS[fmt]
    n = round(T * FPS)
    d = SCRATCH / fmt
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    # frame f cobre t = f*T/n; subframes centrados nele, dentro do obturador
    items = [(((f + SHUTTER * ((s + .5) / SUB - .5)) * T / n) % T, str(d / f"{f * SUB + s:05d}.png"))
             for f in range(n) for s in range(SUB)]
    port = serve()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page = open_page(p, port, w, h, b)
        cues = page.evaluate("CUES")
        browser.close()
    OUT.mkdir(exist_ok=True)
    wav = SCRATCH / f"audio-{fmt}.wav"
    build_audio(info, cues, n / FPS, wav)  # antes dos frames: falha cedo
    shoot_all(port, w, h, b, items)
    out = OUT / f"agennix-{fmt}-{w}x{h}.mp4"
    subprocess.run([
        FFMPEG, "-v", "error", "-y", "-framerate", str(FPS * SUB), "-i", str(d / "%05d.png"), "-i", str(wav),
        "-filter_complex",
        f"[0:v]tmix=frames={SUB},select='eq(mod(n\\,{SUB})\\,{SUB - 1})',setpts=N/({FPS}*TB),"
        "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709[v]",
        "-map", "[v]", "-map", "1:a", "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "14",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    print("ok:", out, f"({n} frames, {n / FPS:.3f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stills", "check", "full"])
    ap.add_argument("--fmt", choices=list(FORMATS), default="square")
    a = ap.parse_args()
    {"stills": lambda: stills(a.fmt), "check": check, "full": lambda: full(a.fmt)}[a.cmd]()
