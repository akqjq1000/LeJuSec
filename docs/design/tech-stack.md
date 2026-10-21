# 기술 스택

## 선정 원칙

- **에이전트는 의존성 없는 단일 바이너리** → 배포·무결성 유지 용이.
- **컨트롤 플레인은 AI 생태계 친화적** → 오케스트레이션·RAG 구현 최적.
- **점검은 기존 검증된 도구 조합** → 바퀴 재발명 금지.
- **LLM은 tool use 중심** → 비용·지연이 중요한 실시간 경로에는 미사용.

## 스택 선택

| 영역 | 권장 | 비고 |
|------|------|------|
| 에이전트 | **Go 1.22+** (정적 단일 바이너리) | 크로스컴파일, self-protection, 무의존 배포 |
| 컨트롤 플레인 | **Python 3.12 + FastAPI** | AI 생태계 연동 최적 |
| LLM 오케스트레이션 | **LangGraph** (분기·HITL 많을 때) / 자체 상태머신 | 단순 체인이면 LangChain |
| LLM | **Claude (Opus/Sonnet 최신)** — tool use 중심 | 도구 라우팅·조치 생성·맥락 판단 |
| 벡터 DB | **Qdrant** 또는 **pgvector** | 소규모면 pgvector로 Postgres 일원화 |
| 자산/결과 DB | **PostgreSQL 16+** | 설정 스냅샷은 Git 병행 |
| 점검 엔진 | **OpenSCAP, Lynis, Trivy, Nmap, OSV-Scanner, Grype** | 래핑하여 사용 |
| 샌드박스 | **Docker/Podman** (OS 설정) + **Firecracker/QEMU** (전체 VM) | |
| 취약점 피드 | **NVD/CVE, OSV, KISA 가이드** | 정기 동기화 파이프라인 |
| 메시징/작업 큐 | **NATS** 또는 **Redis + Celery** | 에이전트↔서버 비동기 작업 |
| 통신 보안 | **mTLS + Ed25519 서명** | 결과 위조 방지 (필수) |
| 시크릿 | **HashiCorp Vault** 또는 클라우드 시크릿 매니저 | 코드/로그 비밀 금지 |
| 관측성 | **OpenTelemetry + Prometheus + Grafana** | |

## 왜 LLM을 모든 곳에 쓰지 않는가

| 경로 | 도구 | 이유 |
|------|------|------|
| 데이터 수집·판정 | 결정론적 코드 | 재현성·감사 |
| 실시간 이상 탐지 (기능 3) | 규칙 + 경량 통계 모델 | 비용·지연 |
| 도구 라우팅·조치 생성 (기능 4·5) | Claude tool use | 추론·생성 가치 큼 |
| 근거 요약·분류 (기능 1·2) | Claude | 비정형 → 구조화 |

## 개발 도구

| 영역 | 도구 |
|------|------|
| Go 린트 | golangci-lint, go vet |
| Python 린트/포맷 | ruff, mypy |
| Python 테스트 | pytest |
| Go 테스트 | go test |
| 컨테이너 | Docker / Podman |
| 보안 스캔 | gosec, bandit, Trivy, gitleaks, CodeQL |
| SBOM | Syft |

관련: [아키텍처](../architecture.md) · [CI/CD](../development/ci-cd.md)
