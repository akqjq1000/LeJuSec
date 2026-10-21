# CI/CD

CI/CD는 GitHub Actions로 구성한다. 워크플로우 파일은 [`.github/workflows/`](../../.github/workflows/)에 있다.

## 파이프라인 개요

```
Push / PR ──▶ ci.yml        (린트 · 테스트 · 빌드)
          └─▶ security.yml  (CodeQL · Trivy · gitleaks · SBOM)
Tag vX.Y.Z ─▶ release.yml   (빌드 · 서명 · 릴리스 아티팩트)
```

모든 워크플로우는 모노레포 상황에 맞춰 **경로 필터 + 디렉터리 존재 가드**를 사용한다.
`agent/`·`control-plane/` 코드가 아직 없어도 워크플로우는 안전하게 통과(스킵)한다.

## ci.yml — 지속적 통합

PR과 `main` 푸시에서 실행.

| Job | 내용 |
|-----|------|
| `agent` | `agent/` 존재 시: golangci-lint, `go vet`, `go test`, `go build` |
| `control-plane` | `control-plane/` 존재 시: ruff(lint+format), mypy, pytest |
| `docs` | Markdown 링크 검사 |

- 캐시: Go 모듈, pip/uv 캐시.
- 병렬 매트릭스: OS(ubuntu), 언어 버전.

## security.yml — 보안 스캔

PR·`main` 푸시·주간 스케줄에서 실행.

| 스캔 | 도구 | 대상 |
|------|------|------|
| 정적 분석(SAST) | CodeQL | Go, Python |
| 비밀 스캔 | gitleaks | 전체 트리·히스토리 |
| 의존성/이미지 취약점 | Trivy | 파일시스템, 컨테이너 이미지 |
| SBOM 생성 | Syft | 릴리스 아티팩트 |

결과는 GitHub Security 탭(SARIF 업로드)에 집계.

## release.yml — 릴리스

`vX.Y.Z` 태그 푸시에서 실행.

1. 에이전트 크로스컴파일 (linux/amd64, linux/arm64).
2. 컨테이너 이미지 빌드·푸시 (GHCR).
3. 아티팩트 서명 (cosign) + SBOM 첨부.
4. CHANGELOG 생성, GitHub Release 발행.

## 비밀 관리

- CI 비밀은 **GitHub Actions Secrets / OIDC**로만 주입. 로그 출력 금지.
- 서명 키는 키리스(cosign OIDC) 또는 시크릿 매니저 사용.
- Dependabot ([dependabot.yml](../../.github/dependabot.yml))으로 의존성·액션 버전 자동 갱신.

## 브랜치 보호 규칙 (권장)

`main` 브랜치:
- PR 필수, 리뷰 1인 이상 승인.
- 필수 상태 체크: `ci.yml`, `security.yml` 그린.
- 서명 커밋 권장, 선형 히스토리(squash) 유지.

## 관련 문서

- [개발 워크플로우](workflow.md) · [기술 스택](../design/tech-stack.md) · [위협 모델](../design/threat-model.md)
