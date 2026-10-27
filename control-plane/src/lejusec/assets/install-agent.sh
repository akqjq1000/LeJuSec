#!/usr/bin/env bash
#
# LeJuSec 에이전트 원샷 설치 스크립트 — 설치 + 등록 + 실행 + 자동 시작을 한 번에.
#
# 대상(점검받을) 시스템에서 한 줄로 실행한다. 컨트롤 플레인이 이 스크립트를
# /install.sh 로 제공하므로 보통 아래처럼 쓴다:
#
#   curl -fsSL http://<컨트롤플레인>:8000/install.sh | sudo bash -s -- --group 운영-웹
#   # 인증이 켜진 경우: ... -- --token <admin-token> --group 운영-웹
#
# 수행: 바이너리 내려받기(릴리스) → 설치 → 키 생성 → 자산 등록 → 공개키 등록
#       → 설정 생성 → 첫 인벤토리 전송 → systemd 타이머로 주기 실행 등록.
# 멱등: 같은 호스트명이면 기존 자산을 재사용하고 공개키만 갱신한다.
#
# 주요 옵션:
#   --server URL         컨트롤 플레인 주소(스크립트를 서버에서 받으면 자동 설정됨)
#   --token TOKEN        운영자 admin 토큰(컨트롤 플레인 인증 활성 시 필요)
#   --group NAME         자산 그룹
#   --role NAME          자산 역할 설명
#   --binary-url URL     에이전트 바이너리 직접 지정(기본: GitHub 릴리스 자동)
#   --agent-bin PATH     이미 있는 로컬 바이너리 사용(다운로드 생략)
#   --ca-cert / --client-cert / --client-key   mTLS(세 값 함께)
#   --poll-interval 15min   주기 실행 간격
#   --no-systemd         systemd 타이머 설치 생략(1회 등록만)
#   --install-dir DIR    바이너리 설치 위치(기본 /usr/local/bin)
#   --config-dir DIR     설정 위치(기본 /etc/lejusec)

set -euo pipefail

REPO="akqjq1000/LeJuSec"

# 서버에서 받은 스크립트에는 아래 자리표시자가 실제 주소로 치환되어 있다.
DEFAULT_SERVER="@@DEFAULT_SERVER@@"
case "$DEFAULT_SERVER" in *"@@"*) DEFAULT_SERVER="" ;; esac

SERVER="${LEJUSEC_SERVER:-$DEFAULT_SERVER}"
HOSTNAME_ARG="${LEJUSEC_HOSTNAME:-$(hostname)}"
GROUP="${LEJUSEC_GROUP:-}"
ROLE="${LEJUSEC_ROLE:-}"
OPERATOR_TOKEN="${LEJUSEC_OPERATOR_TOKEN:-}"
CA_CERT="${LEJUSEC_CA_CERT:-}"
CLIENT_CERT="${LEJUSEC_CLIENT_CERT:-}"
CLIENT_KEY="${LEJUSEC_CLIENT_KEY:-}"
CONFIG_DIR="${LEJUSEC_CONFIG_DIR:-/etc/lejusec}"
INSTALL_DIR="${LEJUSEC_INSTALL_DIR:-/usr/local/bin}"
AGENT_BIN_SRC="${LEJUSEC_AGENT_BIN:-}"
BINARY_URL="${LEJUSEC_BINARY_URL:-}"
POLL_INTERVAL="${LEJUSEC_POLL_INTERVAL:-15min}"
INSTALL_SYSTEMD=1

die() { echo "install-agent: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --server)        SERVER="$2"; shift 2 ;;
    --hostname)      HOSTNAME_ARG="$2"; shift 2 ;;
    --group)         GROUP="$2"; shift 2 ;;
    --role)          ROLE="$2"; shift 2 ;;
    --token)         OPERATOR_TOKEN="$2"; shift 2 ;;
    --binary-url)    BINARY_URL="$2"; shift 2 ;;
    --agent-bin)     AGENT_BIN_SRC="$2"; shift 2 ;;
    --ca-cert)       CA_CERT="$2"; shift 2 ;;
    --client-cert)   CLIENT_CERT="$2"; shift 2 ;;
    --client-key)    CLIENT_KEY="$2"; shift 2 ;;
    --config-dir)    CONFIG_DIR="$2"; shift 2 ;;
    --install-dir)   INSTALL_DIR="$2"; shift 2 ;;
    --poll-interval) POLL_INTERVAL="$2"; shift 2 ;;
    --no-systemd)    INSTALL_SYSTEMD=0; shift ;;
    -h|--help)       sed -n '3,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)               die "알 수 없는 인자: $1 (--help 참고)" ;;
  esac
done

[ -n "$SERVER" ] || die "--server 가 필요합니다 (서버에서 받은 /install.sh 는 자동 설정됨)."
command -v curl >/dev/null 2>&1 || die "curl 이 필요합니다."
[ "$(uname -s)" = "Linux" ] || echo "install-agent: 경고 — Linux 대상에 맞춰졌습니다 (현재 $(uname -s))." >&2

# root 권한 확인(기본 경로는 쓰기에 root 필요).
if [ "$(id -u)" != "0" ]; then
  case "$INSTALL_DIR$CONFIG_DIR" in
    /usr/*|/etc/*) die "root 권한이 필요합니다. sudo 로 실행하세요." ;;
  esac
fi

# mTLS 플래그는 세 값이 모두 있거나 모두 없어야 한다.
if [ -n "$CA_CERT$CLIENT_CERT$CLIENT_KEY" ]; then
  [ -n "$CA_CERT" ] && [ -n "$CLIENT_CERT" ] && [ -n "$CLIENT_KEY" ] \
    || die "--ca-cert / --client-cert / --client-key 는 함께 지정해야 합니다."
fi

# ---- 1) 바이너리 확보 (로컬 → URL → GitHub 릴리스 자동) ------------------------
AGENT_BIN="$INSTALL_DIR/lejusec-agent"
mkdir -p "$INSTALL_DIR"
if [ -n "$AGENT_BIN_SRC" ]; then
  echo "▶ 로컬 바이너리 설치 ($AGENT_BIN_SRC)"
  install -m 0755 "$AGENT_BIN_SRC" "$AGENT_BIN"
else
  # 다운로드 후보: --binary-url 지정 시 그것만, 아니면 (1) 컨트롤 플레인 → (2) GitHub 릴리스.
  if [ -n "$BINARY_URL" ]; then
    urls=("$BINARY_URL")
  else
    case "$(uname -m)" in
      x86_64|amd64)   arch=amd64 ;;
      aarch64|arm64)  arch=arm64 ;;
      *) die "지원하지 않는 아키텍처: $(uname -m) (--binary-url 로 직접 지정)" ;;
    esac
    urls=(
      "$SERVER/agent/lejusec-agent-linux-$arch"
      "https://github.com/$REPO/releases/latest/download/lejusec-agent-linux-$arch"
    )
  fi
  tmp="$(mktemp)"
  ok=0
  for u in "${urls[@]}"; do
    echo "▶ 에이전트 내려받기 ($u)"
    if curl -fSL "$u" -o "$tmp"; then ok=1; break; fi
    echo "  실패 — 다음 후보 시도" >&2
  done
  [ "$ok" = "1" ] || die "바이너리 다운로드 실패. 서버에 'make agent-dist' 로 바이너리를 두거나 --binary-url/--agent-bin 로 지정하세요."
  install -m 0755 "$tmp" "$AGENT_BIN"
  rm -f "$tmp"
fi
"$AGENT_BIN" --version >/dev/null 2>&1 || die "에이전트 실행 확인 실패: $AGENT_BIN"
echo "  설치됨: $AGENT_BIN ($("$AGENT_BIN" --version))"

# ---- curl 공통 플래그 -----------------------------------------------------------
CURL_AUTH=()
[ -n "$OPERATOR_TOKEN" ] && CURL_AUTH=(-H "Authorization: Bearer $OPERATOR_TOKEN")
CURL_TLS=()
[ -n "$CA_CERT" ] && CURL_TLS=(--cacert "$CA_CERT" --cert "$CLIENT_CERT" --key "$CLIENT_KEY")

json_id() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))'
  else
    grep -o '"id"[[:space:]]*:[[:space:]]*[0-9]*' | head -n1 | grep -o '[0-9]*'
  fi
}

# ---- 2) 키 생성 -----------------------------------------------------------------
umask 077
mkdir -p "$CONFIG_DIR"
KEY_PATH="$CONFIG_DIR/agent.key"
if [ -f "$KEY_PATH" ]; then
  die "키가 이미 존재합니다: $KEY_PATH (재설치하려면 삭제 후 다시 실행)."
fi
echo "▶ Ed25519 키 생성 → $KEY_PATH"
PUBKEY="$("$AGENT_BIN" --keygen "$KEY_PATH" | tail -n1)"
[ -n "$PUBKEY" ] || die "공개키 생성 실패."

# ---- 3) 자산 등록 (멱등: 409 면 기존 자산 재사용) -------------------------------
reg_body="$(printf '{"hostname":"%s","role":"%s","group":"%s"}' "$HOSTNAME_ARG" "$ROLE" "$GROUP")"
echo "▶ 자산 등록 ($HOSTNAME_ARG)"
reg_out="$(mktemp)"
reg_code="$(curl -sS -o "$reg_out" -w '%{http_code}' \
  -X POST "$SERVER/assets" -H 'Content-Type: application/json' \
  "${CURL_AUTH[@]}" "${CURL_TLS[@]}" -d "$reg_body" || true)"
if [ "$reg_code" = "201" ]; then
  ASSET_ID="$(json_id < "$reg_out")"
elif [ "$reg_code" = "409" ]; then
  echo "  이미 등록된 호스트명 — 기존 자산을 재사용합니다."
  ASSET_ID="$(curl -sS "$SERVER/assets" "${CURL_AUTH[@]}" "${CURL_TLS[@]}" \
    | { python3 -c 'import sys,json;h=sys.argv[1];print(next((a["id"] for a in json.load(sys.stdin) if a["hostname"]==h),""))' "$HOSTNAME_ARG" \
        2>/dev/null || true; })"
else
  echo "  응답: $(cat "$reg_out")" >&2
  rm -f "$reg_out"; die "자산 등록 실패 (HTTP $reg_code)."
fi
rm -f "$reg_out"
[ -n "${ASSET_ID:-}" ] || die "asset-id 를 확인하지 못했습니다."
echo "  asset-id=$ASSET_ID"

# ---- 4) 공개키 등록 -------------------------------------------------------------
echo "▶ 공개키 등록 (PUT /assets/$ASSET_ID/key)"
key_code="$(curl -sS -o /dev/null -w '%{http_code}' \
  -X PUT "$SERVER/assets/$ASSET_ID/key" -H 'Content-Type: application/json' \
  "${CURL_AUTH[@]}" "${CURL_TLS[@]}" -d "$(printf '{"public_key":"%s"}' "$PUBKEY")" || true)"
[ "$key_code" = "200" ] || die "공개키 등록 실패 (HTTP $key_code)."

# ---- 5) 설정 + 실행 래퍼 생성 ---------------------------------------------------
ENV_FILE="$CONFIG_DIR/agent.env"
echo "▶ 설정 생성 → $ENV_FILE"
cat > "$ENV_FILE" <<EOF
# LeJuSec 에이전트 설정 — install-agent.sh 가 생성 ($(date -u +%Y-%m-%dT%H:%M:%SZ)).
LEJUSEC_SERVER=$SERVER
LEJUSEC_ASSET_ID=$ASSET_ID
LEJUSEC_KEY=$KEY_PATH
LEJUSEC_AGENT_BIN=$AGENT_BIN
LEJUSEC_CA_CERT=$CA_CERT
LEJUSEC_CLIENT_CERT=$CLIENT_CERT
LEJUSEC_CLIENT_KEY=$CLIENT_KEY
EOF
chmod 600 "$ENV_FILE"

RUN_SH="$CONFIG_DIR/agent-run.sh"
cat > "$RUN_SH" <<'EOF'
#!/usr/bin/env bash
# LeJuSec 에이전트 실행 래퍼 — agent.env 를 읽어 플래그를 구성한다.
#   agent-run.sh         # 인벤토리 전송
#   agent-run.sh --poll  # 서버 큐 명령(점검 등) 실행
#   agent-run.sh --apply # 승인된 조치 적용
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$DIR/agent.env"
ARGS=(--server "$LEJUSEC_SERVER" --asset-id "$LEJUSEC_ASSET_ID" --key "$LEJUSEC_KEY")
if [ -n "${LEJUSEC_CA_CERT:-}" ]; then
  ARGS+=(--ca-cert "$LEJUSEC_CA_CERT" --client-cert "$LEJUSEC_CLIENT_CERT" --client-key "$LEJUSEC_CLIENT_KEY")
fi
exec "${LEJUSEC_AGENT_BIN:-lejusec-agent}" "${ARGS[@]}" "$@"
EOF
chmod 755 "$RUN_SH"

# ---- 6) 첫 인벤토리 전송 (연결 확인) -------------------------------------------
echo "▶ 첫 인벤토리 전송"
"$RUN_SH"

# ---- 7) systemd 타이머 (기본 설치) ---------------------------------------------
if [ "$INSTALL_SYSTEMD" = "1" ] && command -v systemctl >/dev/null 2>&1; then
  echo "▶ systemd 타이머 설치 (주기: $POLL_INTERVAL)"
  cat > /etc/systemd/system/lejusec-agent.service <<EOF
[Unit]
Description=LeJuSec agent — inventory + command poll
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$RUN_SH
ExecStart=$RUN_SH --poll
EOF
  cat > /etc/systemd/system/lejusec-agent.timer <<EOF
[Unit]
Description=LeJuSec agent 주기 실행

[Timer]
OnBootSec=2min
OnUnitActiveSec=$POLL_INTERVAL
Persistent=true

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable --now lejusec-agent.timer
  echo "  활성화됨: systemctl status lejusec-agent.timer"
elif [ "$INSTALL_SYSTEMD" = "1" ]; then
  echo "install-agent: systemctl 이 없어 타이머 설치를 건너뜁니다." >&2
fi

echo
echo "✅ 완료 — asset-id=$ASSET_ID"
echo "   설정: $ENV_FILE · 실행 래퍼: $RUN_SH"
