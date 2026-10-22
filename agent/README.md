# Agent

LeJuSec 대상 시스템 에이전트 — 단일 Go 바이너리.
수집(패키지/프로세스/연관 파일) · 점검 실행 · FIM · self-protection.
설계는 [../docs/design/features.md](../docs/design/features.md) 참고.

## 개발

```bash
go build ./...
go test ./...
go run ./cmd/agent --version
go run ./cmd/agent                     # 인벤토리를 JSON으로 출력
```

## 서명 전송

```bash
# 1) 키 생성 (공개키를 컨트롤 플레인에 등록)
go run ./cmd/agent --keygen agent.key
#   → PUT /assets/{id}/key 로 출력된 공개키 등록

# 2) 수집 → 서명 → 전송 (평문)
go run ./cmd/agent --server http://host:8000 --asset-id 1 --key agent.key

# 3) mTLS 전송 (클라이언트 인증서 + CA)
go run ./cmd/agent --server https://host:8000 --asset-id 1 --key agent.key \
  --ca-cert certs/ca.crt --client-cert certs/client.crt --client-key certs/client.key
```

전송 바디(JSON 원본 바이트)에 Ed25519 서명을 붙여 `X-Signature` 헤더로 보내고,
컨트롤 플레인이 등록된 공개키로 검증한다. `--ca-cert/--client-cert/--client-key`를
함께 주면 전송 구간을 상호 TLS로 보호한다.

## 구조

```
cmd/agent/              # 진입점 (main)
internal/collector/     # 호스트 인벤토리 수집 (패키지/프로세스/연관 파일)
internal/signing/       # Ed25519 키 생성·서명
internal/client/        # 서명된 인벤토리 전송 (+ mTLS)
```

바이너리 빌드는 릴리스 워크플로우(`.github/workflows/release.yml`)에서
`linux/amd64`·`linux/arm64`로 크로스컴파일된다.
