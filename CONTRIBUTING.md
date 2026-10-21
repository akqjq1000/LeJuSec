# 기여 가이드

LeJuSec에 기여해 주셔서 감사합니다. 본 문서는 기여 절차를 요약합니다.
상세는 [개발 워크플로우](docs/development/workflow.md)를 참고하세요.

## 시작하기

1. [개발 환경 설정](docs/development/getting-started.md)으로 로컬 환경을 구성합니다.
2. 이슈를 확인하거나 새 이슈를 등록합니다.
3. `main`에서 작업 브랜치를 분기합니다 (`feat/...`, `fix/...` 등).

## 기여 흐름

1. 작은 단위로 커밋 — [Conventional Commits](docs/development/workflow.md#커밋-컨벤션-conventional-commits) 준수.
2. 로컬 점검 통과:
   ```bash
   # Python
   ruff check . && mypy . && pytest
   # Go
   golangci-lint run && go test ./...
   ```
3. PR 생성 — [PR 템플릿](.github/PULL_REQUEST_TEMPLATE.md) 작성, 관련 이슈 연결.
4. CI(린트·테스트·보안 스캔)가 그린인지 확인.
5. 리뷰 승인 후 **squash merge**.

## 코드 스타일

- **Go**: `gofmt`, golangci-lint 규칙 준수.
- **Python**: ruff(포맷·린트), mypy 타입 체크 통과.
- 공개 함수·모듈에 docstring/주석 — 주변 코드의 밀도와 관례에 맞춤.

## 설계 원칙 (리뷰에서 확인)

- **결정론 우선, LLM 보조** — 판정·수집은 코드, 추론·생성은 LLM.
- **최소 권한 + allowlist** — LLM 임의 명령 실행 경로 금지.
- **HITL** — 조치 반영은 사람 승인 후.

자세한 배경은 [설계 개요](docs/design/overview.md) 참고.

## 보안 이슈

보안 취약점은 **공개 이슈로 등록하지 마세요.** [SECURITY.md](SECURITY.md)의 비공개 신고 절차를 따릅니다.

## 행동 강령

상호 존중을 기본으로 합니다. 괴롭힘·차별적 언행은 허용되지 않습니다.

## 라이선스

기여한 코드는 프로젝트의 [MIT 라이선스](LICENSE)로 배포됩니다.
