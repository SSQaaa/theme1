#!/usr/bin/env bash

# One-click launcher for Theme1 stack on Orange Pi.
# What it does:
# 1) Ask for Orange Pi IP (or use --ip) and update HA_URL in /home/orangepi/Desktop/theme1/ai_assistent/HA.py
# 2) Run audio sink setup commands
# 3) Scan and connect OpenBCI WiFi AP if found
# 4) Open 4 separate terminals with required commands
#
# Boot mode (for systemd):
#   ./start_theme1_stack.sh --ip 192.168.31.159 --headless

set -u

HA_FILE="/home/orangepi/Desktop/theme1/ai_assistent/HA.py"
OPENBCI_IFACE="wlx90de80e3f9df"
OPENBCI_SSID="OpenBCI WiFi AP"
OPENBCI_PASS="abcd1234*"
LOG_DIR="/home/orangepi/Desktop/theme1/ui/backend/logs"

CMD_1='source "$HOME/miniforge3/etc/profile.d/conda.sh" 2>/dev/null || source "$HOME/anaconda3/etc/profile.d/conda.sh" 2>/dev/null; conda activate themeone; cd /home/orangepi/Desktop/theme1/ai_assistent/rknn-llm-release-v1.2.3/examples/rkllm_server_demo/rkllm_server; python flask_server.py --rkllm_model_path /home/orangepi/Desktop/theme1/ai_assistent/KunKun_W8A8_RK3588_1_3_2.rkllm --target_platform rk3588'
CMD_2='source "$HOME/miniforge3/etc/profile.d/conda.sh" 2>/dev/null || source "$HOME/anaconda3/etc/profile.d/conda.sh" 2>/dev/null; conda activate themeone; cd /home/orangepi/Desktop/theme1/ui/backend; uvicorn server:app --host 0.0.0.0 --port 8000'
CMD_3='source "$HOME/miniforge3/etc/profile.d/conda.sh" 2>/dev/null || source "$HOME/anaconda3/etc/profile.d/conda.sh" 2>/dev/null; conda activate base; export ASSISTANT_EVENT_URL="http://127.0.0.1:8000/api/assistant/event"; cd /home/orangepi/Desktop/theme1/ai_assistent; python main.py'
CMD_4='docker ps || sudo -n docker ps || true'
HEADLESS=0
IP_INPUT=""

log() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*"
}

err() {
  echo "[ERROR] $*" >&2
}

usage() {
  cat <<'EOF'
Usage:
  ./start_theme1_stack.sh [--ip <ipv4>] [--headless]

Options:
  --ip <ipv4>   Set HA_URL IP without interactive prompt.
  --headless    Do not open GUI terminals; run commands in background and log to files.
  -h, --help    Show this help.
EOF
}

is_valid_ipv4() {
  local ip="$1"
  [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  local IFS='.'
  local part
  for part in $ip; do
    ((part >= 0 && part <= 255)) || return 1
  done
  return 0
}

open_terminal() {
  local title="$1"
  local cmd="$2"
  local wrapped_cmd="${cmd}; echo; echo 'Process finished in ${title}. Press Enter to close.'; read -r _"

  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -lc "$wrapped_cmd" &
    return 0
  fi
  if command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title="$title" --hold --command="bash -lc '$cmd'" &
    return 0
  fi
  if command -v mate-terminal >/dev/null 2>&1; then
    mate-terminal --title="$title" -- bash -lc "$wrapped_cmd" &
    return 0
  fi
  if command -v konsole >/dev/null 2>&1; then
    konsole --new-tab -p tabtitle="$title" -e bash -lc "$wrapped_cmd" &
    return 0
  fi
  if command -v lxterminal >/dev/null 2>&1; then
    lxterminal --title="$title" --command="bash -lc '$cmd; exec bash'" &
    return 0
  fi
  if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -T "$title" -e bash -lc "$wrapped_cmd" &
    return 0
  fi

  return 1
}

update_ha_url() {
  local new_ip="$1"

  if [[ ! -f "$HA_FILE" ]]; then
    err "HA file not found: $HA_FILE"
    return 1
  fi

  local backup="${HA_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
  cp "$HA_FILE" "$backup"
  log "Backup created: $backup"

  # Replace only IP part in HA_URL = "http://<ip>:8123"
  if ! sed -E -i "s#^(HA_URL[[:space:]]*=[[:space:]]*\"http://)[0-9.]+(:8123\")#\1${new_ip}\2#" "$HA_FILE"; then
    err "Failed to update HA_URL in $HA_FILE"
    return 1
  fi

  local updated_line
  updated_line="$(grep -E '^HA_URL[[:space:]]*=' "$HA_FILE" || true)"
  if [[ -n "$updated_line" ]]; then
    log "Updated HA_URL line: $updated_line"
  else
    warn "HA_URL line not found after update. Please check file manually."
  fi
}

setup_audio_sink() {
  log "Setting audio sink to ES8388"
  pactl set-default-sink alsa_output.platform-es8388-sound.stereo-fallback || warn "Failed: set-default-sink"
  pactl set-sink-mute alsa_output.platform-es8388-sound.stereo-fallback 0 || warn "Failed: set-sink-mute"
  pactl set-sink-volume alsa_output.platform-es8388-sound.stereo-fallback 90% || warn "Failed: set-sink-volume"
}

connect_openbci_wifi() {
  log "Scanning WiFi on interface ${OPENBCI_IFACE}"
  local scan_output
  scan_output="$(nmcli dev wifi list ifname "$OPENBCI_IFACE" 2>&1)"
  echo "$scan_output"

  if echo "$scan_output" | grep -Fq "$OPENBCI_SSID"; then
    log "Found SSID: ${OPENBCI_SSID}. Connecting..."
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
      nmcli dev wifi connect "$OPENBCI_SSID" password "$OPENBCI_PASS" ifname "$OPENBCI_IFACE" || warn "WiFi connect command failed"
    elif sudo -n true >/dev/null 2>&1; then
      sudo -n nmcli dev wifi connect "$OPENBCI_SSID" password "$OPENBCI_PASS" ifname "$OPENBCI_IFACE" || warn "WiFi connect command failed"
    else
      nmcli dev wifi connect "$OPENBCI_SSID" password "$OPENBCI_PASS" ifname "$OPENBCI_IFACE" || warn "WiFi connect command failed (no sudo -n, tried current user)"
    fi
  else
    warn "SSID not found: ${OPENBCI_SSID}. Skipping connect."
  fi
}

open_all_terminals() {
  if [[ "$HEADLESS" -eq 1 ]]; then
    mkdir -p "$LOG_DIR"
    log "Headless mode enabled. Starting commands in background."
    nohup bash -lc "$CMD_1" > "${LOG_DIR}/terminal1_rkllm_server.log" 2>&1 &
    nohup bash -lc "$CMD_2" > "${LOG_DIR}/terminal2_backend.log" 2>&1 &
    nohup bash -lc "$CMD_3" > "${LOG_DIR}/terminal3_assistant.log" 2>&1 &
    bash -lc "$CMD_4" > "${LOG_DIR}/terminal4_docker_ps.log" 2>&1 || true
    log "Started. Logs are in: $LOG_DIR"
    return 0
  fi

  if [[ -z "${DISPLAY:-}" ]]; then
    warn "DISPLAY is empty. Switching to headless start."
    HEADLESS=1
    open_all_terminals
    return $?
  fi

  log "Opening terminal 1: RKLLM flask server"
  open_terminal "theme1-voice-server" "$CMD_1" || err "Failed to open terminal 1"
  sleep 0.5

  log "Opening terminal 2: UI backend"
  open_terminal "theme1-backend" "$CMD_2" || err "Failed to open terminal 2"
  sleep 0.5

  log "Opening terminal 3: AI assistant main"
  open_terminal "theme1-assistant" "$CMD_3" || err "Failed to open terminal 3"
  sleep 0.5

  log "Opening terminal 4: docker status"
  open_terminal "theme1-docker" "$CMD_4" || err "Failed to open terminal 4"
}

main() {
  local ip=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ip)
        shift
        [[ $# -gt 0 ]] || { err "Missing value after --ip"; exit 1; }
        IP_INPUT="$1"
        ;;
      --headless)
        HEADLESS=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        err "Unknown argument: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done

  if [[ -n "$IP_INPUT" ]]; then
    ip="$IP_INPUT"
  else
    read -r -p "Enter Orange Pi IP for HA_URL (example 192.168.31.159): " ip
  fi

  if ! is_valid_ipv4 "$ip"; then
    err "Invalid IPv4 address: $ip"
    exit 1
  fi

  update_ha_url "$ip" || exit 1
  setup_audio_sink
  connect_openbci_wifi
  open_all_terminals

  log "All requested steps finished."
}

main "$@"
