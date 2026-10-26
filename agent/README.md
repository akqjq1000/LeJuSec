# Agent

LeJuSec 대상 시스템 에이전트 — 단일 Go 바이너리.
수집(패키지/프로세스/연관 파일) · 점검 실행 · FIM · self-protection.
설계는 [../docs/design/features.md](../docs/design/features.md) 참고.

인벤토리에는 자동 탐지한 OS 정보(`host`: Linux는 `/etc/os-release`의 `ID`/`VERSION_ID`,
그 외는 `runtime.GOOS`/`GOARCH`)가 함께 담겨 전송된다. 컨트롤 플레인은 이 값으로 자산의
`os`/`os_version`을 자동 채우므로, 운영자는 자산 등록 시 OS를 입력하지 않아도 된다.

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

## 점검(스캔) 실행

에이전트가 스캐너를 직접 실행/수집해 정규화 finding을 `/scan`으로 전송한다
(판정은 컨트롤 플레인 룰 엔진이 수행).

```bash
# 로컬 확인 (수집 결과 JSON 출력)
go run ./cmd/agent --scan --scan-path / --lynis-report /var/log/lynis-report.dat

# 서명 전송 (+ mTLS)
go run ./cmd/agent --scan --scan-path / \
  --oscap-results results.xml --lynis-report /var/log/lynis-report.dat \
  --server https://host:8000 --asset-id 1 --key agent.key \
  --ca-cert certs/ca.crt --client-cert certs/client.crt --client-key certs/client.key
```

- `--scan-path`: `trivy fs` 대상 경로(trivy 설치 시). 비우면 생략.
- `--lynis-report`: 기존 Lynis 리포트 `.dat` 경로. 비우면 생략.
- `--oscap-results`: OpenSCAP XCCDF 결과 XML 경로. 비우면 생략.

## 무결성 점검(FIM)

모니터링 대상 파일의 SHA-256 매니페스트(+에이전트 자체 해시)를 만들어 전송한다.
컨트롤 플레인이 중앙 베이스라인과 비교해 변조를 탐지한다.

```bash
# 로컬 확인
go run ./cmd/agent --fim --fim-paths /etc/passwd,/etc/ssh/sshd_config

# 서명 전송 (첫 전송은 베이스라인으로 설정, 이후 변경 탐지)
go run ./cmd/agent --fim --server https://host:8000 --asset-id 1 --key agent.key \
  --ca-cert certs/ca.crt --client-cert certs/client.crt --client-key certs/client.key
```

`--fim-paths` 생략 시 핵심 설정 파일(/etc/passwd, /etc/shadow, /etc/ssh/sshd_config,
/etc/sudoers, /etc/crontab)을 점검한다.

## 조치 적용(--apply)

승인된 조치를 에이전트가 가져와 대상에 적용하고 결과를 보고한다(실패 시 롤백).
로컬 denylist로 위험 스크립트를 한 번 더 차단한다(컨트롤 플레인 정적분석에 더해).

```bash
go run ./cmd/agent --apply --server https://host:8000 --asset-id 1 --key agent.key \
  --ca-cert certs/ca.crt --client-cert certs/client.crt --client-key certs/client.key
```

`pull`(승인·미적용 조치 수신) → 적용/롤백 → `report`(결과 보고) 모두 서명 전송이다.

## 구조

```
cmd/agent/              # 진입점 (main; inventory / --scan / --fim / --apply)
internal/collector/     # 호스트 인벤토리 수집 (패키지/프로세스/연관 파일)
internal/scan/          # 스캐너 실행·파싱 (Trivy/Lynis/OpenSCAP) → Finding
internal/fim/           # 파일 무결성 매니페스트(SHA-256 + 자체 해시)
internal/remediate/     # 승인 조치 적용(+롤백), 로컬 denylist
internal/signing/       # Ed25519 키 생성·서명
internal/client/        # 서명된 인벤토리/스캔/무결성/조치 전송 (+ mTLS)
```

바이너리 빌드는 릴리스 워크플로우(`.github/workflows/release.yml`)에서
`linux/amd64`·`linux/arm64`로 크로스컴파일된다.
