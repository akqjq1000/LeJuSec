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

## 원샷 설치 (권장)

대상(점검받을) 시스템에서 **한 줄**로 설치·등록·실행·자동 시작까지 끝낸다.
컨트롤 플레인이 설치 스크립트를 `/install.sh` 로 제공하며, 서버 주소는 자동으로 채워진다.

```bash
# 인증 비활성(개발)
curl -fsSL http://<컨트롤플레인>:8000/install.sh | sudo bash -s -- --group 운영-웹

# 인증 활성 — admin 운영자 토큰 전달
curl -fsSL http://<컨트롤플레인>:8000/install.sh | sudo bash -s -- --token <admin-token> --group 운영-웹

# mTLS
curl -fsSL https://<컨트롤플레인>:8000/install.sh | sudo bash -s -- --token <admin-token> \
  --ca-cert /etc/lejusec/ca.crt --client-cert /etc/lejusec/client.crt --client-key /etc/lejusec/client.key
```

스크립트가 수행하는 일: 에이전트 바이너리 내려받기(아키텍처 자동 판별)
→ `/usr/local/bin/lejusec-agent` 설치 → Ed25519 키 생성 → 자산 등록 → 공개키 등록
→ 설정 생성 → 첫 인벤토리 전송 → systemd 타이머 2개 등록(점검/인벤토리 + 헬스체크 하트비트).

- **hostname 자동**: 등록 시 hostname을 보내지 않는다. 서버가 임시 식별자를 부여하고,
  에이전트 첫 통신(인벤토리)에서 보고된 hostname/주소(IP)로 자동 교체한다
  (`--hostname` 으로 명시 지정도 가능).
- **헬스체크 + 명령 poll**: 1분 주기(타이머)로 `--heartbeat`(생존 신호)와 `--poll`(서버
  큐의 검사 명령 수신·실행)을 함께 수행한다. 덕분에 GUI "검사 요청"이 약 1분 내 처리된다
  (`--heartbeat-interval`/`LEJUSEC_HEARTBEAT_INTERVAL` 로 주기 조정). 인벤토리 수집은
  별도 15분 주기 타이머.

> **바이너리 출처**: 설치 스크립트는 ① 컨트롤 플레인(`GET /agent/...`) → ② GitHub
> 릴리스 순으로 내려받는다. 릴리스를 아직 발행하지 않은 자체 호스팅 환경에서는 서버에서
> `make agent-dist` 를 한 번 실행해 `dist/` 에 바이너리를 만들어 두면 컨트롤 플레인이
> 바로 제공한다(컨테이너로 띄웠다면 `dist/` 를 `/app/dist` 로 마운트). 이미 빌드한
> 바이너리가 있으면 `--agent-bin PATH` 또는 `--binary-url URL` 로 바로 지정할 수도 있다.

생성물: `/etc/lejusec/agent.env`(설정), `/etc/lejusec/agent-run.sh`(실행 래퍼),
`lejusec-agent.timer`(주기 실행). 이후 수동 실행은 래퍼로 한다 — `agent-run.sh`(인벤토리),
`agent-run.sh --poll`(명령 실행), `agent-run.sh --apply`(조치 적용).

주요 옵션: `--group/--role`(자산 분류), `--poll-interval 15min`(주기), `--no-systemd`(1회 등록만),
`--binary-url`/`--agent-bin`(바이너리 직접 지정), `--install-dir`/`--config-dir`.
설정 형식은 [agent.env.example](agent.env.example) 참고.

아래는 바이너리를 직접 다룰 때의 수동 절차다.

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
