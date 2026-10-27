.PHONY: help cp-install cp-lint cp-test agent-build agent-test up down certs cp-run cp-run-tls \
	dev dev-tls stack-up stack-down stack-build

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
	@echo "dev          컨트롤 플레인 + 웹 콘솔 한 번에 실행"
	@echo "dev-tls      dev + 컨트롤 플레인 mTLS (certs/ 필요)"
	@echo "stack-up     전체 스택(DB+API+웹) 컨테이너 기동 (docker compose)"
	@echo "stack-down   전체 스택 컨테이너 중지"
	@echo "stack-build  전체 스택 이미지 빌드"

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

# 컨트롤 플레인 + 웹 콘솔을 한 번에 실행 (Ctrl+C로 전체 종료)
dev:
	python scripts/dev.py

dev-tls:
	python scripts/dev.py --tls

# 전체 스택(Postgres + 컨트롤 플레인 + 웹)을 컨테이너로 기동/중지/빌드
stack-up:
	docker compose -f deploy/compose.yml up -d --build

stack-down:
	docker compose -f deploy/compose.yml down

stack-build:
	docker compose -f deploy/compose.yml build
