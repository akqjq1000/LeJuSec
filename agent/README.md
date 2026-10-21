# Agent

LeJuSec 대상 시스템 에이전트 — 단일 Go 바이너리.
수집(패키지/프로세스/연관 파일) · 점검 실행 · FIM · self-protection.
설계는 [../docs/design/features.md](../docs/design/features.md) 참고.

## 개발

```bash
go build ./...
go test ./...
go run ./cmd/agent --version
```

## 구조

```
cmd/agent/              # 진입점 (main)
internal/collector/     # 호스트 인벤토리 수집 (Phase 1 골격)
```

바이너리 빌드는 릴리스 워크플로우(`.github/workflows/release.yml`)에서
`linux/amd64`·`linux/arm64`로 크로스컴파일된다.
