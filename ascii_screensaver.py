#!/usr/bin/env python3
"""ascii_screensaver.py — a multi-effect terminal screensaver engine.

Effects: rotating shaded 3D torus, wireframe polyhedra, hyperspace
starfield, boids murmuration, data-stream rain, and a fire simulation.
Cycles through effects automatically; Ctrl+C exits cleanly.

Usage:
    python3 ascii_screensaver.py                  cycle everything
    python3 ascii_screensaver.py torus            single effect
    python3 ascii_screensaver.py warp,flock,fire  custom order
    python3 ascii_screensaver.py --list           list effects
    python3 ascii_screensaver.py --duration 20    seconds per effect
"""

import argparse
import math
import random
import shutil
import sys
import threading
import time

TAU = math.tau
RAMP = ".,-~:;=!*#%@"
FIRE_COLORS = [16, 52, 88, 124, 160, 196, 202, 208, 214, 220, 226,
               227, 228, 229, 230, 231]
RAINBOW = [196, 202, 208, 214, 220, 226, 190, 154, 118, 82, 46, 47,
           48, 49, 50, 51, 45, 39, 33, 27, 21, 57, 93, 129, 165, 201,
           200, 199, 198, 197]
CARD_TIME = 2.6


class Screen:
    def __init__(self, w, h):
        self.resize(w, h)

    def resize(self, w, h):
        self.w = w
        self.h = h

    def clear(self):
        self.chars = [[" "] * self.w for _ in range(self.h)]
        self.cols = [[0] * self.w for _ in range(self.h)]

    def set(self, x, y, ch, c=0):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.chars[y][x] = ch
            self.cols[y][x] = c

    def center(self, y, s, c=0):
        x = (self.w - len(s)) // 2
        for i, ch in enumerate(s):
            self.set(x + i, y, ch, c)

    def dump(self):
        out = ["\x1b[H"]
        for crow, orow in zip(self.chars, self.cols):
            line = []
            last = -1
            for ch, c in zip(crow, orow):
                if c != last:
                    line.append("\x1b[39m" if c == 0 else "\x1b[38;5;%dm" % c)
                    last = c
                line.append(ch)
            out.append("".join(line).rstrip())
            out.append("\n")
        out.append("\x1b[0m")
        return "".join(out)


class Torus:
    NAME = "TORUS FIELD"
    SUB = "real-time 3d projection · z-buffer · lambert shading"

    def __init__(self, scr):
        self.scr = scr
        self.t = random.random() * 10.0
        self.ax = 0.9
        self.ay = 0.4

    def update(self, dt):
        self.t += dt
        self.ax += dt * 0.85
        self.ay += dt * 0.5

    def draw(self):
        s = self.scr
        w, h = s.w, s.h
        zb = [0.0] * (w * h)
        chb = [" "] * (w * h)
        clb = [0] * (w * h)
        R1, R2, K2 = 1.0, 2.0, 5.0
        K1 = min(w * K2 * 3.0 / (8 * (R1 + R2)),
                 (h * 2) * K2 * 3.0 / (8 * (R1 + R2)))
        cx, cy = w / 2.0, h / 2.0
        ca, sa = math.cos(self.ax), math.sin(self.ax)
        cb, sb = math.cos(self.ay), math.sin(self.ay)
        Lx, Ly, Lz = 0.4082, 0.8165, -0.4082
        n_theta, n_phi = 26, 80
        hue_shift = int(self.t * 18.0)
        for ti in range(n_theta):
            th = TAU * ti / n_theta
            ct, st = math.cos(th), math.sin(th)
            ring_r = R2 + R1 * ct
            ny0, nz0 = R1 * st, 0.0
            nn_y, nn_z = st, 0.0
            for pi in range(n_phi):
                ph = TAU * pi / n_phi
                cp, sp_ = math.cos(ph), math.sin(ph)
                px = ring_r * cp
                pz = ring_r * sp_
                y1 = ny0 * ca - nz0 * sa
                z1 = ny0 * sa + nz0 * ca
                x2 = px * cb + z1 * sb
                z2 = -px * sb + z1 * cb
                depth = K2 + z2
                if depth <= 0.25:
                    continue
                ox = int(cx + K1 * x2 / depth)
                oy = int(cy + K1 * y1 / depth * 0.5)
                if not (0 <= ox < w and 0 <= oy < h):
                    continue
                nx = ct * cp
                nzn = ct * sp_
                n1y = nn_y * ca - nn_z * sa
                n1z = nn_y * sa + nn_z * ca
                nx2 = nx * cb + n1z * sb
                nz2 = -nx * sb + n1z * cb
                lum = nx * Lx + n1y * Ly + nz2 * Lz
                if lum <= 0.0:
                    continue
                idx = oy * w + ox
                zi = 1.0 / depth
                if zi > zb[idx]:
                    zb[idx] = zi
                    li = int(lum * (len(RAMP) - 0.01))
                    if li >= len(RAMP):
                        li = len(RAMP) - 1
                    chb[idx] = RAMP[max(li, 1)]
                    clb[idx] = RAINBOW[(pi * len(RAINBOW) // n_phi
                                        + ti * 3 + hue_shift) % len(RAINBOW)]
        for idx in range(w * h):
            if zb[idx] > 0.0:
                s.chars[idx // w][idx % w] = chb[idx]
                s.cols[idx // w][idx % w] = clb[idx]


def _icosa_verts():
    g = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [(-1, g, 0), (1, g, 0), (-1, -g, 0), (1, -g, 0),
           (0, -1, g), (0, 1, g), (0, -1, -g), (0, 1, -g),
           (g, 0, -1), (g, 0, 1), (-g, 0, -1), (-g, 0, 1)]
    n = math.sqrt(1.0 + g * g)
    return [(x / n, y / n, z / n) for x, y, z in raw]


def _edges_by_proximity(verts):
    edges = []
    best = None
    for i in range(len(verts)):
        for j in range(i + 1, len(verts)):
            d = math.dist(verts[i], verts[j])
            if best is None or d < best - 1e-6:
                best = d
                edges = [(i, j)]
            elif abs(d - best) < 1e-6:
                edges.append((i, j))
    return edges


SHAPES = [
    ("CUBE", lambda: ([(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                       (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
                      [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
                       (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)])),
    ("OCTAHEDRON", lambda: ([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                             (0, 0, 1), (0, 0, -1)],
                            [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3),
                             (1, 4), (1, 5), (2, 4), (2, 5), (3, 4), (3, 5)])),
    ("TETRAHEDRON", lambda: ([(1, 1, 1), (1, -1, -1), (-1, 1, -1),
                              (-1, -1, 1)],
                             [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3),
                              (2, 3)])),
    ("ICOSAHEDRON", lambda: (_icosa_verts(),
                             _edges_by_proximity(_icosa_verts()))),
]


class Wireframe:
    NAME = "SOLID STATE"
    SUB = "rotating polyhedra · perspective wireframes"

    def __init__(self, scr):
        self.scr = scr
        self.t = 0.0
        self.shape_idx = 0
        self.shape_t = 0.0

    def update(self, dt):
        self.t += dt
        self.shape_t += dt
        if self.shape_t > 7.0:
            self.shape_t = 0.0
            self.shape_idx = (self.shape_idx + 1) % len(SHAPES)

    def draw(self):
        name, fn = SHAPES[self.shape_idx]
        verts, edges = fn()
        s = self.scr
        t = self.t
        rx = t * 0.7
        ry = t * 0.95
        rz = t * 0.35
        cxr, sxr = math.cos(rx), math.sin(rx)
        cyr, syr = math.cos(ry), math.sin(ry)
        czr, szr = math.cos(rz), math.sin(rz)
        proj = []
        d = 4.2
        span = max(abs(v) for v in verts[0]) * 1.05
        K1 = min(s.w * d * 0.42, s.h * 2 * d * 0.42) / span
        cx, cy = s.w / 2.0, s.h / 2.0
        hue_base = int(t * 14.0) % len(RAINBOW)
        for x, y, z in verts:
            y1 = y * cxr - z * sxr
            z1 = y * sxr + z * cxr
            x2 = x * cyr + z1 * syr
            z2 = -x * syr + z1 * cyr
            x3 = x2 * czr - y1 * szr
            y3 = x2 * szr + y1 * czr
            depth = d + z2
            proj.append((cx + K1 * x3 / depth,
                         cy + K1 * y3 / depth / 2.0, depth))
        for ei, (a, b) in enumerate(edges):
            xa, ya, za = proj[a]
            xb, yb, zb_ = proj[b]
            steps = max(2, int(max(abs(xb - xa), abs(yb - ya)) * 1.4))
            edge_hue = RAINBOW[(hue_base + ei * 7) % len(RAINBOW)]
            for k in range(steps + 1):
                f = k / steps
                px = xa + (xb - xa) * f
                py = ya + (yb - ya) * f
                pd = za + (zb_ - za) * f
                xi, yi = int(px), int(py)
                if 0 <= xi < s.w and 0 <= yi < s.h:
                    rel = max(0.0, min(1.0, (d + span - pd) / (2 * span)))
                    ri = int(rel * (len(RAMP) - 1))
                    s.set(xi, yi, RAMP[ri], edge_hue)


class Warp:
    NAME = "HYPERSPACE"
    SUB = "faster-than-light starfield"

    def __init__(self, scr):
        self.scr = scr
        self.stars = []
        for _ in range(340):
            self.stars.append(self._new_star(initial=True))

    @staticmethod
    def _new_star(initial=False):
        return {
            "x": random.uniform(-1.0, 1.0),
            "y": random.uniform(-1.0, 1.0),
            "z": random.random() if initial else 1.0,
            "c": random.choice([231, 231, 255, 195, 153, 189, 231]),
        }

    def update(self, dt):
        for i, st in enumerate(self.stars):
            st["z"] -= dt * 0.42
            if st["z"] <= 0.06:
                self.stars[i] = self._new_star()

    def draw(self):
        s = self.scr
        w, h = s.w, s.h
        cx, cy = w / 2.0, h / 2.0
        fx, fy = w * 0.62, h * 0.31
        for st in self.stars:
            z = st["z"]
            sx = cx + st["x"] / z * fx
            sy = cy + st["y"] / z * fy
            z2 = min(z + 0.09, 1.0)
            hx = cx + st["x"] / z2 * fx
            hy = cy + st["y"] / z2 * fy
            dist = math.hypot(sx - hx, sy - hy)
            steps = max(1, int(dist))
            near = 1.0 - z
            head_c = st["c"]
            tail_c = 240 if near < 0.55 else 245
            for k in range(steps + 1):
                f = k / steps
                xi = int(hx + (sx - hx) * f)
                yi = int(hy + (sy - hy) * f)
                if 0 <= xi < w and 0 <= yi < h:
                    if k == steps and near > 0.75:
                        s.set(xi, yi, "@", head_c)
                    elif k == steps and near > 0.45:
                        s.set(xi, yi, "*", head_c)
                    else:
                        s.set(xi, yi, "." if near < 0.35 else "-", tail_c)


class Flock:
    NAME = "MURMURATION"
    SUB = "boids · separation · alignment · cohesion"
    PALETTE = [51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38,
               37, 36, 35, 33, 32, 31]
    SECTORS = (">", "\\", "v", "/", "<", "\\", "^", "/")

    def __init__(self, scr):
        self.scr = scr
        self.boids = []
        for _ in range(min(72, max(24, scr.w * scr.h // 90))):
            ang = random.uniform(0, TAU)
            sp = random.uniform(7.0, 12.0)
            self.boids.append({
                "x": random.uniform(0, scr.w),
                "y": random.uniform(0, scr.h),
                "vx": math.cos(ang) * sp,
                "vy": math.sin(ang) * sp,
                "hue": random.choice(self.PALETTE),
            })

    def update(self, dt):
        w, h = self.scr.w, self.scr.h
        r2 = 81.0
        sep2 = 6.5
        for b in self.boids:
            ax = ay = cx = cy = cnt = 0.0
            sxp = syp = 0.0
            for o in self.boids:
                if o is b:
                    continue
                dx = o["x"] - b["x"]
                dy = o["y"] - b["y"]
                if dx > w / 2:
                    dx -= w
                elif dx < -w / 2:
                    dx += w
                if dy > h / 2:
                    dy -= h
                elif dy < -h / 2:
                    dy += h
                d2 = dx * dx + dy * dy
                if d2 < r2:
                    ax += o["vx"]
                    ay += o["vy"]
                    cx += dx
                    cy += dy
                    cnt += 1
                    if d2 < sep2 and d2 > 0.0001:
                        inv = 1.0 / d2
                        sxp -= dx * inv
                        syp -= dy * inv
            if cnt:
                b["vx"] += ((ax / cnt - b["vx"]) * 1.1
                            + cx / cnt * 0.28
                            + sxp * 26.0) * dt * 2.4
                b["vy"] += ((ay / cnt - b["vy"]) * 1.1
                            + cy / cnt * 0.28
                            + syp * 26.0) * dt * 2.4
            else:
                wander = random.uniform(-0.6, 0.6)
                b["vx"] += wander * dt
                b["vy"] += wander * dt
        for b in self.boids:
            sp = math.hypot(b["vx"], b["vy"]) or 1e-6
            target = min(max(sp, 7.0), 15.0)
            scale = target / sp
            b["vx"] *= scale
            b["vy"] *= scale
            b["x"] = (b["x"] + b["vx"] * dt) % w
            b["y"] = (b["y"] + b["vy"] * dt) % h

    def draw(self):
        s = self.scr
        for b in self.boids:
            ang = math.atan2(b["vy"], b["vx"])
            sector = int(((ang + math.pi / 8) % TAU) / (TAU / 8)) % 8
            tx = int(b["x"] - b["vx"] * 0.16)
            ty = int(b["y"] - b["vy"] * 0.32)
            s.set(tx, ty, ".", 238)
            s.set(int(b["x"]), int(b["y"]),
                  self.SECTORS[sector], b["hue"])


GLYPHS = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*+-=<>/\\|?"


class Rain:
    NAME = "DATA STREAM"
    SUB = "intercepted transmission feed"

    def __init__(self, scr):
        self.scr = scr
        self.drops = []
        for x in range(scr.w):
            if random.random() < 0.82:
                self.drops.append(self._make(x, scr.h))

    @staticmethod
    def _make(x, h):
        ln = random.randint(max(4, h // 6), max(6, h * 2 // 3))
        return {
            "x": x,
            "head": random.uniform(-ln, 0),
            "sp": random.uniform(6.0, 20.0),
            "len": ln,
            "glyphs": [random.choice(GLYPHS) for _ in range(ln)],
        }

    def update(self, dt):
        h = self.scr.h
        alive = []
        for d in self.drops:
            d["head"] += d["sp"] * dt
            for _ in range(3):
                gi = random.randrange(d["len"])
                d["glyphs"][gi] = random.choice(GLYPHS)
            if d["head"] - d["len"] < h + 2:
                alive.append(d)
            elif random.random() < 0.04:
                alive.append(self._make(d["x"], h))
        self.drops = alive
        while len(self.drops) < self.scr.w * 0.5:
            x = random.randrange(self.scr.w)
            self.drops.append(self._make(x, h))

    def draw(self):
        s = self.scr
        for d in self.drops:
            x = d["x"]
            head = int(d["head"])
            for k in range(d["len"]):
                y = head - k
                if 0 <= y < s.h:
                    if k == 0:
                        s.set(x, y, d["glyphs"][k], 231)
                    elif k < 3:
                        s.set(x, y, d["glyphs"][k], 118)
                    elif k < 6:
                        s.set(x, y, d["glyphs"][k], 40)
                    elif k < d["len"] // 2:
                        s.set(x, y, d["glyphs"][k], 28)
                    else:
                        s.set(x, y, d["glyphs"][k], 22)


class Fire:
    NAME = "ETERNAL FLAME"
    SUB = "cellular heat propagation · rising embers"

    def __init__(self, scr):
        self.scr = scr
        self.heat = [0] * (scr.w * (scr.h + 1))
        self.embers = []

    def update(self, dt):
        s = self.scr
        w, h = s.w, s.h
        base = w * h
        for x in range(w):
            v = random.choice((30, 33, 35, 36, 36, 34))
            self.heat[base + x] = v
        mid = int(h * 0.52)
        new = [0] * len(self.heat)
        new[base:base + w] = self.heat[base:base + w]
        for y in range(h):
            decay = random.randint(0, 1) if y >= mid else random.randint(1, 3)
            below = (y + 1) * w
            row = y * w
            for x in range(w):
                xm = (x - 1) % w
                xp = (x + 1) % w
                v = (self.heat[below + x] + self.heat[below + xm]
                     + self.heat[below + xp]) // 3 - decay
                new[row + x] = v if v > 0 else 0
        self.heat = new
        if random.random() < 0.65:
            self.embers.append({
                "x": random.uniform(0, w),
                "y": h - 1.0,
                "vy": -random.uniform(5.0, 11.0),
                "ph": random.uniform(0, TAU),
                "life": random.uniform(1.5, 3.5),
            })
        alive = []
        for e in self.embers:
            e["life"] -= dt
            e["y"] += e["vy"] * dt
            e["x"] += math.sin(e["y"] * 0.35 + e["ph"]) * 6.0 * dt
            if e["life"] > 0 and e["y"] > 0:
                alive.append(e)
        self.embers = alive

    def draw(self):
        s = self.scr
        w, h = s.w, s.h
        nramp = len(FIRE_COLORS) - 1
        for y in range(0, h):
            row = y * w
            for x in range(w):
                hv = self.heat[row + x]
                if hv > 1:
                    ci = hv * nramp // 36
                    ri = hv * (len(RAMP) - 1) // 36
                    if ri == 0:
                        continue
                    s.set(x, y, RAMP[ri], FIRE_COLORS[min(ci, nramp)])
        for e in self.embers:
            ch = "*" if e["life"] > 1.2 else "."
            s.set(int(e["x"]), int(e["y"]), ch, 214 if e["life"] > 0.8 else 208)


EFFECTS = {
    "torus": Torus,
    "wire": Wireframe,
    "warp": Warp,
    "flock": Flock,
    "rain": Rain,
    "fire": Fire,
}
DEFAULT_ORDER = ["torus", "wire", "warp", "flock", "rain", "fire"]


def draw_card(scr, eff_name, sub):
    bw = min(scr.w - 4, max(len(eff_name), len(sub)) + 10)
    bh = 7
    x0 = (scr.w - bw) // 2
    y0 = (scr.h - bh) // 2
    for x in range(x0 + 1, x0 + bw - 1):
        scr.set(x, y0, "-", 250)
        scr.set(x, y0 + bh - 1, "-", 250)
    for y in range(y0 + 1, y0 + bh - 1):
        scr.set(x0, y, "|", 250)
        scr.set(x0 + bw - 1, y, "|", 250)
    for ch, dx, dy in (("+", 0, 0), ("+", bw - 1, 0),
                       ("+", 0, bh - 1), ("+", bw - 1, bh - 1)):
        scr.set(x0 + dx, y0 + dy, ch, 250)
    scr.center(y0 + 2, eff_name, 231)
    scr.center(y0 + 4, sub, 245)


class KeyWatcher:
    def __init__(self):
        self.triggered = False
        self.ok = False
        try:
            import select
            import termios
            import tty
            self.select = select
            self.termios = termios
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
            self.ok = True
        except Exception:
            pass

    def start(self):
        if self.ok:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            r, _, _ = self.select.select([self.fd], [], [], 0.2)
            if r:
                sys.stdin.read(1)
                self.triggered = True
                return

    def restore(self):
        if self.ok:
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old)


def run(order, fps, duration, card):
    interval = 1.0 / fps
    print("\x1b[?1049h\x1b[?25l\x1b[2J", end="")
    sys.stdout.flush()
    scr = None
    eff = None
    idx = 0
    eff_t = 0.0
    last = time.monotonic()
    watcher = KeyWatcher()
    watcher.start()
    try:
        while True:
            if watcher.triggered:
                break
            now = time.monotonic()
            dt = min(0.05, now - last)
            last = now
            cols, rows = shutil.get_terminal_size()
            if scr is None or cols != scr.w or rows != scr.h:
                scr = Screen(cols, rows)
                eff = EFFECTS[order[idx]](scr)
                eff_t = 0.0
                print("\x1b[2J", end="")
            eff.update(dt)
            eff_t += dt
            scr.clear()
            eff.draw()
            if card and eff_t < CARD_TIME:
                draw_card(scr, eff.NAME, eff.SUB)
            sys.stdout.write(scr.dump())
            sys.stdout.flush()
            if duration > 0 and eff_t >= duration and len(order) > 1:
                idx = (idx + 1) % len(order)
                eff = EFFECTS[order[idx]](scr)
                eff_t = 0.0
                print("\x1b[2J", end="")
            spent = time.monotonic() - now
            time.sleep(max(0.0, interval - spent))
    except KeyboardInterrupt:
        pass
    finally:
        watcher.restore()
        print("\x1b[?25h\x1b[?1049l", end="")
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="multi-effect ASCII screensaver")
    ap.add_argument("mode", nargs="?",
                    help="effect name or comma-separated order")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--duration", type=float, default=18.0,
                    help="seconds per effect before cycling (default 18)")
    ap.add_argument("--no-card", action="store_true",
                    help="hide the title card between effects")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for key, cls in EFFECTS.items():
            print("%-8s %s" % (key, cls.NAME))
        return

    if args.mode:
        keys = [m.strip().lower() for m in args.mode.split(",")]
        for k in keys:
            if k not in EFFECTS:
                ap.error("unknown effect %r (try --list)" % k)
        order = keys
    else:
        order = list(DEFAULT_ORDER)

    try:
        run(order, max(1.0, args.fps), args.duration, not args.no_card)
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
