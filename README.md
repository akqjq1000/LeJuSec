# LeJuSec

> 생성형 AI 기반 취약점 점검 자동화 플랫폼
> *AI-assisted vulnerability assessment & remediation automation*

[![CI](https://github.com/akqjq1000/LeJuSec/actions/workflows/ci.yml/badge.svg)](https://github.com/akqjq1000/LeJuSec/actions/workflows/ci.yml)
[![Security](https://github.com/akqjq1000/LeJuSec/actions/workflows/security.yml/badge.svg)](https://github.com/akqjq1000/LeJuSec/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 개요

LeJuSec는 시스템 취약점 점검 과정을 생성형 AI로 자동화하는 플랫폼입니다.
기존 보안 점검 도구(OpenSCAP, Lynis, Trivy 등)가 **실제 점검**을 수행하고,
LLM은 **도구 선택 · 조치안 생성 · 맥락 판단 · 근거 제시**를 담당하는
**"결정론적 엔진 + LLM 보조"** 하이브리드 구조를 따릅니다.

### 핵심 설계 원칙

1. **결정론 우선, LLM 보조** — 수집·판정·해시는 코드로, 추론·분류·생성·계획은 LLM으로.
2. **Human-in-the-loop (HITL)** — 조치의 실제 적용은 항상 사람 승인 게이트를 통과.
3. **최소 권한 + Allowlist** — 에이전트와 LLM 모두 허용된 작업만 수행. LLM이 임의 셸 명령을 생성·실행하는 구조는 금지.

## 주요 기능

| # | 기능 | 설명 | AI 비중 |
|---|------|------|---------|
| 1 | RAG 기반 점검 · 버전 관리 | 점검 기준(KISA/CIS/STIG) 검색, 자산 등록/해제, 설정 스냅샷 버전 관리 | 중 |
| 2 | 프로세스 · 연관 파일 탐색 | 패키지/소스 설치 식별, 설정·로그 파일 자동 매핑 | 중 |
| 3 | 무결성 유지 · 부정행위 탐지 | FIM(파일 무결성), 변조·점검 회피 징후 판단 | 하 |
| 4 | 점검 도구 자동 선택 | 대상 프로파일에 맞는 스캐너 라우팅 | 상 |
| 5 | 조치안 생성 · 샌드박스 검증 | 조치 스크립트 생성 후 격리 환경에서 검증, 롤백 동시 생성 | 상 |

자세한 설계는 [docs/design/overview.md](docs/design/overview.md)를 참고하세요.

### 점검 기준 지식베이스 (RAG 코퍼스)

RAG 근거 검색 코퍼스는 두 파일을 병합해 구성한다
([control-plane/src/lejusec/knowledge/](control-plane/src/lejusec/knowledge/)).

- `checks.json` — 스캐너(OpenSCAP/Lynis/Trivy)와 연동되는 자동 판정 점검
- `kisa_unix.json` — KISA『주요정보통신기반시설 기술적 취약점 분석·평가 방법 상세가이드』의
  **Unix 부분 전체(U-01~U-67, 계정·파일/디렉터리·서비스·패치·로그 관리)**를 RAG 근거로 등록한
  지식 항목. 스캐너 연동이 없는 수동 점검(`rule_type: "manual"`)이라 룰 엔진 판정에는 포함되지
  않고 `/checks/search`(RAG) 검색에만 쓰인다.

## 아키텍처

```
Control Plane (중앙 서버)
  ├─ 자산/CMDB (PostgreSQL)
  ├─ RAG 지식베이스 (Vector DB)
  ├─ Orchestrator (LLM Agent: 도구 라우팅 · 조치 생성 · 판단)
  ├─ 점검 기준/결과 버전 저장소 (DB + Git)
  └─ Sandbox Runner (Container / VM)
          ↕  mTLS · 서명된 작업/결과
Agent (대상 시스템, Go 단일 바이너리)
  └─ 수집 · 점검 실행 · FIM · self-protection
```

전체 다이어그램과 데이터 흐름은 [docs/architecture.md](docs/architecture.md)에 있습니다.

## 저장소 구조

```
LeJuSec/
├─ agent/            # 대상 시스템 에이전트 (Go)
├─ control-plane/    # 컨트롤 플레인 API/오케스트레이터 (Python, FastAPI)
├─ web/              # 운영자 콘솔 GUI (React + TypeScript, Vite) — G1
├─ docs/             # 설계·개발·운영 문서
│  ├─ architecture.md
│  ├─ roadmap.md
│  ├─ design/        # 개요·기능·위협모델·기술스택
│  └─ development/   # 개발 환경·워크플로우·CI/CD
├─ .github/          # CI/CD 워크플로우, 이슈/PR 템플릿
├─ CONTRIBUTING.md
├─ SECURITY.md
└─ LICENSE
```

## 사전 요구사항

- Python 3.12+ (컨트롤 플레인), uv 또는 pip
- Go 1.22+ (에이전트)
- Node 20+ (웹 콘솔)
- (선택) Docker/Podman — 로컬 의존 서비스(Postgres/pgvector, Qdrant)

> 기본 DB는 외부 의존 없이 바로 뜨도록 SQLite를 쓴다. PostgreSQL은
> `LEJUSEC_DATABASE_URL`(`postgresql+psycopg://...`)로 주입한다.

## 시스템 구동 방법

### 0. 한 번에 실행 (권장 · 개발용)

컨트롤 플레인(API)과 웹 콘솔을 한 번에 띄운다. 두 프로세스의 로그가 `[cp]`/`[web]`
접두어로 합쳐져 출력되고, `Ctrl+C` 한 번으로 전부 종료된다.

```bash
make dev                 # = python scripts/dev.py
# 옵션:
python scripts/dev.py --tls      # 컨트롤 플레인을 mTLS로 (certs/ 필요)
python scripts/dev.py --no-web   # 컨트롤 플레인만
python scripts/dev.py --no-cp    # 웹 콘솔만
```

> 전제: `make cp-install`(컨트롤 플레인)과 `cd web && npm install`(웹)로 의존성을
> 설치해 둔다. 컨트롤 플레인은 `control-plane/.venv`가 있으면 그 파이썬을 사용한다.

컨테이너로 전체 스택(DB+API+웹)을 한 번에 띄우려면 아래 [Docker Compose](#6-docker-compose-전체-스택) 참고.

아래 1~4는 각 구성요소를 개별 실행하는 방법이다.

### 1. 컨트롤 플레인 (API)

```bash
cd control-plane
uv venv
source .venv/Scripts/activate              # Git Bash(MINGW64). PowerShell: .venv\Scripts\Activate.ps1 · Linux/macOS: source .venv/bin/activate
uv pip install -e ".[dev]"                 # lejusec 설치(필수)
python -m lejusec.server                   # http://127.0.0.1:8000  (/healthz)
```

> venv를 활성화하지 않고 시스템 Python으로 실행하면 `ModuleNotFoundError: No module
> named 'lejusec'`가 난다. 활성화 없이 쓰려면 `.venv/Scripts/python.exe -m lejusec.server`.

### 2. 웹 콘솔 (운영자 GUI)

```bash
cd web
npm install
npm run dev                                # http://localhost:5173
```

컨트롤 플레인은 CORS에서 `http://localhost:5173`을 기본 허용한다.

### 3. 에이전트 (대상 시스템)

```bash
cd agent
go build -o lejusec-agent ./cmd/agent

# (1) 키 생성 → 출력된 공개키를 등록에 사용
./lejusec-agent --keygen agent.key

# (2) 자산 등록 + 공개키 등록 (운영자/API)
#     OS는 입력하지 않아도 된다 — 에이전트가 인벤토리를 보고할 때 자동 탐지된다.
#     (등록 직후에는 os="pending" 상태이며, 첫 인벤토리 수신 시 ubuntu/24.04 등으로 채워진다.)
curl -X POST http://127.0.0.1:8000/assets \
  -H 'Content-Type: application/json' -d '{"hostname":"host-01"}'
curl -X PUT http://127.0.0.1:8000/assets/1/key \
  -H 'Content-Type: application/json' -d '{"public_key":"<공개키>"}'

# (3) 서명 전송 — 인벤토리 / 점검 / 무결성
./lejusec-agent --server http://127.0.0.1:8000 --asset-id 1 --key agent.key
./lejusec-agent --scan --server http://127.0.0.1:8000 --asset-id 1 --key agent.key \
  --lynis-report /var/log/lynis-report.dat --oscap-results results.xml
./lejusec-agent --fim  --server http://127.0.0.1:8000 --asset-id 1 --key agent.key
```

### 4. mTLS로 구동 (권장)

```bash
# 개발용 인증서 생성 (CA / 서버 / 클라이언트)
cd control-plane && python scripts/gen_certs.py --out ../certs \
  --server-san DNS:localhost --server-san IP:127.0.0.1

# 컨트롤 플레인 (상호 TLS)
LEJUSEC_TLS_CERTFILE=../certs/server.crt LEJUSEC_TLS_KEYFILE=../certs/server.key \
LEJUSEC_TLS_CA_CERTS=../certs/ca.crt python -m lejusec.server

# 에이전트 (클라이언트 인증서)
./lejusec-agent --server https://localhost:8000 --asset-id 1 --key agent.key \
  --ca-cert certs/ca.crt --client-cert certs/client.crt --client-key certs/client.key
```

### 5. (선택) 의존 서비스 · 단축 명령

```bash
docker compose -f deploy/compose.dev.yml up -d   # Postgres/pgvector, Qdrant (의존 서비스만)
make help                                        # dev / cp-run / certs / up / stack-up ...
```

### 6. Docker Compose (전체 스택)

Postgres + 컨트롤 플레인 + 웹 콘솔을 컨테이너로 한 번에 띄운다.

```bash
docker compose -f deploy/compose.yml up -d --build   # = make stack-up
# 웹 콘솔:        http://localhost:8080
# 컨트롤 플레인:  http://localhost:8000  (/healthz)
docker compose -f deploy/compose.yml down            # = make stack-down
```

> 웹 이미지는 빌드 타임에 `VITE_API_BASE`(기본 `http://localhost:8000`)로 API 주소를
> 주입하고, 컨트롤 플레인은 `compose.dev.yml`과 달리 Postgres에 연결된다. 로컬 개발
> 편의용 구성이며 비밀값·TLS는 운영 시 별도 주입해야 한다.

전체 운영 흐름: **자산 등록 → 에이전트 수집·점검 → 룰 엔진 판정 → 조치 생성·검증·승인(HITL) → 무결성 모니터링**. 운영자 콘솔(웹)에서 한눈에 확인·승인한다.
상세 개발 절차는 [docs/development/getting-started.md](docs/development/getting-started.md) 참고.

## 문서

- [설계 개요 및 실현 가능성](docs/design/overview.md)
- [기능 상세 설계](docs/design/features.md)
- [위협 모델](docs/design/threat-model.md)
- [기술 스택](docs/design/tech-stack.md)
- [GUI 구현 계획](docs/design/gui-plan.md)
- [아키텍처](docs/architecture.md)
- [개발 로드맵](docs/roadmap.md)
- [개발 환경 설정](docs/development/getting-started.md)
- [개발 워크플로우](docs/development/workflow.md)
- [CI/CD](docs/development/ci-cd.md)
- [기여 가이드](CONTRIBUTING.md)
- [보안 정책](SECURITY.md)

## 라이선스

[MIT](LICENSE) © 2026 LeJus
