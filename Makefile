.PHONY: help cp-install cp-lint cp-test agent-build agent-test up down certs cp-run cp-run-tls

help:
	@echo "cp-install   컨트롤 플레인 의존성 설치"
	@echo "cp-lint      ruff + mypy"
	@echo "cp-test      pytest"
	@echo "agent-build  go build"
	@echo "agent-test   go test"
	@echo "up / down    로컬 의존 서비스 기동/중지 (docker compose)"
	@echo "certs        개발용 mTLS 인증서 생성 (certs/)"
	@echo "cp-run       컨트롤 플레인 평문 HTTP 기동"
	@echo "cp-run-tls   컨트롤 플레인 mTLS 기동 (certs/ 필요)"

cp-install:
	cd control-plane && pip install -e ".[dev]"

cp-lint:
	cd control-plane && ruff check . && ruff format --check . && mypy src tests

cp-test:
	cd control-plane && pytest -q

agent-build:
	cd agent && go build ./...

agent-test:
	cd agent && go test ./...

up:
	docker compose -f deploy/compose.dev.yml up -d

down:
	docker compose -f deploy/compose.dev.yml down

certs:
	cd control-plane && python scripts/gen_certs.py --out ../certs \
	  --server-san DNS:localhost --server-san IP:127.0.0.1

cp-run:
	cd control-plane && python -m lejusec.server

cp-run-tls:
	cd control-plane && LEJUSEC_TLS_CERTFILE=../certs/server.crt \
	  LEJUSEC_TLS_KEYFILE=../certs/server.key \
	  LEJUSEC_TLS_CA_CERTS=../certs/ca.crt python -m lejusec.server
