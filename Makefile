.PHONY: help cp-install cp-lint cp-test agent-build agent-test up down

help:
	@echo "cp-install   컨트롤 플레인 의존성 설치"
	@echo "cp-lint      ruff + mypy"
	@echo "cp-test      pytest"
	@echo "agent-build  go build"
	@echo "agent-test   go test"
	@echo "up / down    로컬 의존 서비스 기동/중지 (docker compose)"

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
