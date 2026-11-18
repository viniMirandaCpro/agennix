"""Grade de batidas de uma faixa, so com numpy.

uso: python3 beats.py faixa.mp3 [--bars 8] [--json saida.json]
Decodifica via ffmpeg, mede tempo por autocorrelacao do fluxo espectral,
acha a fase do compasso pela energia grave (bumbo) e escolhe a janela de
N compassos mais cheia que comeca numa batida forte. Cada batida e
refinada para o pico de onset medido mais proximo (+-35 ms).
"""
import json
import os
import subprocess
import sys

import numpy as np

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
SR = 22050
HOP = 128  # ~5.8 ms


def decode(path, sr=SR):
    raw = subprocess.run(
        [FFMPEG, "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, np.float32)


def spectra(x, n=1024):
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::HOP]
    return np.abs(np.fft.rfft(frames * np.hanning(n), axis=1))


def flux(mag, lo=0, hi=None):
    m = np.log1p(100 * mag[:, lo:hi])
    d = np.maximum(np.diff(m, axis=0), 0).sum(1)
    d = np.concatenate([[0], d])
    k = 16  # remove a tendencia lenta
    return np.maximum(d - np.convolve(d, np.ones(k) / k, "same"), 0)


def analyze(path, bars=8):
    x = decode(path)
    mag = spectra(x)
    fps = SR / HOP
    on = flux(mag)
    low = flux(mag, 0, int(150 / (SR / 1024)))  # < 150 Hz: bumbo

    # tempo: autocorrelacao do onset entre 90 e 150 BPM
    o = on - on.mean()
    F = np.fft.rfft(o, 2 * len(o))
    ac = np.fft.irfft(F * np.conj(F))[:len(o)]
    lags = np.arange(len(ac))
    bpm_of = 60 * fps / np.maximum(lags, 1)
    ok = (bpm_of > 90) & (bpm_of < 150)
    lag = lags[ok][np.argmax(ac[ok])]
    # refina o periodo com interpolacao parabolica
    a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
    lag_f = lag + 0.5 * (a - c) / (a - 2 * b + c)
    period = lag_f / fps

    # fase: pente de impulsos que maximiza o onset
    n = len(on)
    phases = np.linspace(0, period, 200, endpoint=False)
    score = [on[np.clip(((np.arange(p, n / fps, period)) * fps).astype(int), 0, n - 1)].sum() for p in phases]
    phase = phases[int(np.argmax(score))]
    grid = np.arange(phase, n / fps - period, period)

    # refina cada batida para o pico local medido
    def peak(t, env, win=0.035):
        i0, i1 = int((t - win) * fps), int((t + win) * fps)
        i0, i1 = max(i0, 0), min(i1, n - 1)
        return (i0 + int(np.argmax(env[i0:i1 + 1]))) / fps if i1 > i0 else t

    beats = np.array([peak(t, on) for t in grid])

    # batida forte: fase de compasso (mod 4) com mais energia grave
    low_at = np.array([low[min(int(t * fps), n - 1)] for t in beats])
    bar_phase = int(np.argmax([low_at[k::4].sum() for k in range(4)]))

    # janela de N compassos cheia e estavel, comecando numa batida forte que abre secao
    c = np.concatenate([[0], np.cumsum(x.astype(np.float64) ** 2)])
    bar_rms = lambda i: np.sqrt((c[int(beats[i + 4] * SR)] - c[int(beats[i] * SR)]) / ((beats[i + 4] - beats[i]) * SR))
    need = bars * 4
    best = None
    for s in range(bar_phase + 8, len(beats) - need - 4, 4):
        r = np.array([bar_rms(s + 4 * k) for k in range(bars)])
        e = r.mean() * (1 - r.std() / (r.mean() + 1e-9))
        before = np.mean([bar_rms(s - 8), bar_rms(s - 4)])
        e *= 1 + max(r[:2].mean() - before, 0) / (r.mean() + 1e-9)  # entrada de secao
        e *= 1 + 0.5 * low_at[s] / (low_at.max() + 1e-9)  # bumbo forte
        if best is None or e > best[0]:
            best = (e, s)
    s = best[1]
    win = beats[s:s + need + 1]
    reg = np.polyfit(np.arange(len(grid)), grid, 1)
    return {
        "file": path,
        "bpm": round(60 / period, 3),
        "start": float(win[0]),
        "beats": [round(float(t - win[0]), 4) for t in win],  # relativo ao inicio, 33 valores
        "jitter_ms": round(float(np.abs(beats - np.polyval(reg, np.arange(len(grid)))).std() * 1000), 2),
        "fill": round(float(best[0]), 4),
    }


if __name__ == "__main__":
    args = sys.argv[1:]
    bars = int(args[args.index("--bars") + 1]) if "--bars" in args else 8
    out = args[args.index("--json") + 1] if "--json" in args else None
    files = [a for a in args if a.endswith((".mp3", ".wav"))]
    res = [analyze(f, bars) for f in files]
    for r in res:
        print(f'{r["file"]}: {r["bpm"]} BPM, inicio {r["start"]:.3f}s, jitter {r["jitter_ms"]} ms, cheio {r["fill"]}')
    if out:
        json.dump(res[0], open(out, "w"), indent=1)
