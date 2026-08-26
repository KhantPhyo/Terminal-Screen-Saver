#!/bin/bash
# ascii_screensaver_watch.sh — launches the ASCII screensaver (wire,warp)
# in the user's active terminal app after IDLE_LIMIT seconds of no input.
# Any key press exits the screensaver and drops back to a shell prompt.

IDLE_LIMIT="${ASCII_SA_IDLE:-120}"
CHECK_INTERVAL="${ASCII_SA_CHECK:-10}"
RETURN_THRESHOLD=60
LOG="/tmp/ascii-screensaver.log"

log() { echo "$(date '+%H:%M:%S') $*" >> "$LOG"; }

SS_CMD="python3 $HOME/ascii_screensaver.py wire,warp --duration 25 --no-card"

idle_seconds() {
    ioreg -c IOHIDSystem -dE | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'
}

launch_iterm2() {
    log "trying iTerm2..."
    osascript <<EOF 2>>"$LOG"
tell application id "com.googlecode.iterm2"
    activate
    create window with default profile
    tell current session of current window to write text "$SS_CMD; printf '\\n[screensaver stopped — press ⌘W to close]\\n'; exec zsh"
end tell
EOF
    local rc=$?
    log "iTerm2 result rc=$rc"
    return $rc
}

launch_ghostty() {
    log "trying Ghostty (direct exec)..."
    nohup /Applications/Ghostty.app/Contents/MacOS/ghostty -e zsh -c "$SS_CMD; printf '\n[screensaver stopped — press ⌘W to close]\n'; exec zsh" >>"$LOG" 2>&1 &
    local rc=$?
    log "Ghostty result rc=$rc"
    return $rc
}

launch_terminal() {
    osascript \
        -e "tell application \"Terminal\" to do script \"$SS_CMD; exec zsh\"" \
        -e 'tell application "Terminal" to activate' >/dev/null 2>&1
}

launch_screensaver() {
    if pgrep -xq "ghostty"; then
        launch_ghostty && return 0
        launch_iterm2 && return 0
    elif pgrep -xq "iTerm2"; then
        launch_iterm2 && return 0
        launch_ghostty && return 0
    fi
    launch_terminal
}

while true; do
    idle=$(idle_seconds)
    log "tick idle=${idle:-none} limit=$IDLE_LIMIT"
    if [ "${idle:-0}" -ge "$IDLE_LIMIT" ] && ! pgrep -f "ascii_screensaver.py" >/dev/null; then
        log "TRIGGER — launching screensaver"
        launch_screensaver
        sleep 10
        while :; do
            idle=$(idle_seconds)
            [ "${idle:-999}" -lt "$RETURN_THRESHOLD" ] && break
            sleep 5
        done
        sleep 5
    fi
    sleep "$CHECK_INTERVAL"
done
