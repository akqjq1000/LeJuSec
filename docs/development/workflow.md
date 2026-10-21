# 개발 워크플로우

## 브랜치 전략 (Trunk-based + 짧은 수명 브랜치)

- `main` — 항상 배포 가능 상태. 보호 브랜치(직접 푸시 금지, PR + 리뷰 필수).
- 작업 브랜치 — `main`에서 분기, 짧은 수명 유지.

### 브랜치 네이밍

```
feat/<요약>      새 기능       예: feat/agent-collector
fix/<요약>       버그 수정     예: fix/mtls-handshake
docs/<요약>      문서          예: docs/threat-model
chore/<요약>     빌드/설정     예: chore/ci-cache
refactor/<요약>  리팩터링
test/<요약>      테스트
```

## 커밋 컨벤션 (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`, `build`
- **scope** (선택): `agent`, `control-plane`, `rag`, `sandbox`, `docs` 등
- 예: `feat(agent): add package collector for rpm/dpkg`

## Pull Request 흐름

1. `main`에서 작업 브랜치 생성.
2. 작은 단위로 커밋, 로컬 점검 통과.
3. PR 생성 — [PR 템플릿](../../.github/PULL_REQUEST_TEMPLATE.md) 작성.
4. CI 통과 ([ci-cd.md](ci-cd.md)): 린트·테스트·보안 스캔 그린.
5. 리뷰 1인 이상 승인.
6. **Squash merge** → `main`. 브랜치 삭제.

### PR 체크리스트

- [ ] 관련 이슈 연결
- [ ] 테스트 추가/갱신
- [ ] 문서 갱신 (해당 시)
- [ ] 보안 영향 검토 (비밀 노출·권한·입력 검증)
- [ ] CI 그린

## 이슈 관리

- 버그: [bug report 템플릿](../../.github/ISSUE_TEMPLATE/bug_report.md)
- 기능: [feature request 템플릿](../../.github/ISSUE_TEMPLATE/feature_request.md)
- 보안 취약점: **이슈로 공개하지 말 것.** [SECURITY.md](../../SECURITY.md) 절차 따름.

## 코드 리뷰 기준

- 결정론 경로와 LLM 경로의 책임 분리가 지켜지는가.
- 입력 검증, allowlist, 서명/암호화가 적용되는가.
- 비밀이 코드·로그에 들어가지 않는가.
- 테스트가 동작을 증명하는가.

## 릴리스

- `main`에 태그 `vX.Y.Z` (SemVer) → [release 워크플로우](ci-cd.md#릴리스) 트리거.
- CHANGELOG는 Conventional Commits에서 생성.

## 관련 문서

- [개발 환경 설정](getting-started.md) · [CI/CD](ci-cd.md) · [기여 가이드](../../CONTRIBUTING.md)
