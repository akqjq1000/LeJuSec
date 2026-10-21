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

> 참고: `agent/`, `control-plane/`는 현재 설계 단계이며, 코드는
> [로드맵](docs/roadmap.md)의 MVP 순서에 따라 추가됩니다.

## 빠른 시작

### 사전 요구사항

- Go 1.22+ (에이전트)
- Python 3.12+ (컨트롤 플레인)
- Docker / Podman (샌드박스, 로컬 의존 서비스)
- PostgreSQL 16+, 벡터 DB(pgvector 또는 Qdrant)

### 개발 환경 구성

```bash
git clone https://github.com/akqjq1000/LeJuSec.git
cd LeJuSec
# 상세 절차는 docs/development/getting-started.md 참고
```

전체 절차는 [docs/development/getting-started.md](docs/development/getting-started.md)를 따르세요.

## 문서

- [설계 개요 및 실현 가능성](docs/design/overview.md)
- [기능 상세 설계](docs/design/features.md)
- [위협 모델](docs/design/threat-model.md)
- [기술 스택](docs/design/tech-stack.md)
- [아키텍처](docs/architecture.md)
- [개발 로드맵](docs/roadmap.md)
- [개발 환경 설정](docs/development/getting-started.md)
- [개발 워크플로우](docs/development/workflow.md)
- [CI/CD](docs/development/ci-cd.md)
- [기여 가이드](CONTRIBUTING.md)
- [보안 정책](SECURITY.md)

## 라이선스

[MIT](LICENSE) © 2026 LeJus
