# 개발 환경 설정

## 사전 요구사항

| 도구 | 버전 | 용도 |
|------|------|------|
| Go | 1.22+ | 에이전트 빌드 |
| Python | 3.12+ | 컨트롤 플레인 |
| uv 또는 pip | 최신 | Python 의존성 |
| Docker / Podman | 최신 | 샌드박스, 로컬 의존 서비스 |
| PostgreSQL | 16+ | 자산/결과 DB (Docker로 기동 가능) |
| golangci-lint, ruff, mypy | 최신 | 린트 |

## 저장소 클론

```bash
git clone https://github.com/akqjq1000/LeJuSec.git
cd LeJuSec
```

## 컨트롤 플레인 (Python / FastAPI)

```bash
cd control-plane
uv venv
# 가상환경 활성화 — 셸에 맞게 하나 선택
source .venv/Scripts/activate        # Git Bash (MINGW64, Windows)
# PowerShell:     .venv\Scripts\Activate.ps1
# cmd:            .venv\Scripts\activate.bat
# Linux · macOS:  source .venv/bin/activate
uv pip install -e ".[dev]"           # lejusec 설치 (필수)
cp .env.example .env                 # 로컬 설정 (비밀은 커밋 금지)
uvicorn lejusec.main:app --reload    # 또는: python -m lejusec.server
```

> **`ModuleNotFoundError: No module named 'lejusec'`** 는 대개 ① venv를 활성화하지
> 않고 시스템 Python으로 실행했거나 ② `uv pip install -e .`를 하지 않은 경우다.
> venv를 활성화하지 않고 쓰려면 venv의 Python을 직접 지정한다:
> `.venv/Scripts/python.exe -m lejusec.server` (Git Bash) /
> `.venv\Scripts\python.exe -m lejusec.server` (PowerShell·cmd).

## 에이전트 (Go)

```bash
cd agent
go mod download
go build ./...
go test ./...
```

## 로컬 의존 서비스 (Docker Compose)

```bash
docker compose -f deploy/compose.dev.yml up -d   # Postgres, 벡터 DB 등
```

## 비밀/시크릿 취급

- `.env`, 인증서, API 키는 **절대 커밋하지 않는다**. `.gitignore`로 제외.
- 로컬에서는 `.env`, 운영/CI에서는 시크릿 매니저(Vault 등) 사용.
- 커밋 전 `gitleaks detect`로 비밀 유출 여부 점검 권장.

## 사전 커밋 점검 (권장)

```bash
# Python
ruff check . && ruff format --check . && mypy .
pytest
# Go
golangci-lint run && go test ./...
```

## 관련 문서

- [개발 워크플로우](workflow.md)
- [CI/CD](ci-cd.md)
- [기여 가이드](../../CONTRIBUTING.md)
