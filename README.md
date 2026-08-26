# ascii-terminal-screensaver

A multi-effect ASCII screensaver for the macOS terminal, written in pure
Python (stdlib only, no dependencies).

![effects](https://img.shields.io/badge/effects-6-blueviolet) ![deps](https://img.shields.io/badge/dependencies-0-success)

## Effects

| Key     | Name        | What it does |
|---------|-------------|--------------|
| `torus` | Torus Field | Real-time 3D torus with z-buffering and Lambert shading |
| `wire`  | Solid State | Rotating wireframe polyhedra (cube, octahedron, tetrahedron, icosahedron) |
| `warp`  | Hyperspace  | FTL starfield with motion streaks |
| `flock` | Murmuration | Boids flocking (separation / alignment / cohesion) |
| `rain`  | Data Stream | Matrix-style rain with glowing heads and glyph mutation |
| `fire`  | Eternal Flame | Cellular heat propagation with rising embers |

## Manual usage

```bash
python3 ascii_screensaver.py                  # cycle all effects (18 s each)
python3 ascii_screensaver.py torus            # single effect
python3 ascii_screensaver.py warp,flock,fire  # custom order
python3 ascii_screensaver.py --duration 30    # seconds per effect
python3 ascii_screensaver.py --fps 60         # frame rate
python3 ascii_screensaver.py --list           # list effects
```

Press **any key** to exit.

## Auto-start on idle (macOS)

Two layers of automation:

1. **In-tab screensaver** — add this to your `~/.zshrc` so any idle zsh tab
   runs the screensaver inside itself after 2 minutes; any key returns you
   to the shell:

   ```zsh
   ASCII_SA_IDLE_SECONDS="${ASCII_SA_IDLE_SECONDS:-120}"
   TMOUT="$ASCII_SA_IDLE_SECONDS"
   TRAPALRM() {
     [[ -t 0 && -t 1 ]] || return 0
     [[ -o interactive ]] || return 0
     python3 "$HOME/ascii_screensaver.py" wire,warp --duration 25 --no-card </dev/tty >/dev/tty 2>&1
   }
   ```

2. **Background watcher** — opens a new window in your running terminal app
   (Ghostty preferred, then iTerm2, then Terminal.app) when the whole Mac has
   been idle and no screensaver is already running:

   ```bash
   # test with a short threshold
   ASCII_SA_IDLE=10 ./ascii_screensaver_watch.sh

   # run permanently: create ~/Library/LaunchAgents/com.user.ascii-screensaver.plist
   # with ProgramArguments ["/bin/bash", "/path/to/ascii_screensaver_watch.sh"],
   # RunAtLoad + KeepAlive true, then:
   launchctl load ~/Library/LaunchAgents/com.user.ascii-screensaver.plist
   ```

Debug log: `/tmp/ascii-screensaver.log`.

## Requirements

- Python 3.8+ (stdlib only)
- macOS (watcher uses `ioreg`, `osascript`, LaunchAgents) — the Python
  screensaver itself works on Linux terminals too
