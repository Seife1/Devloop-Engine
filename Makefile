.PHONY: dev test lint inspect
dev:     ; python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
test:    ; pytest -q
lint:    ; ruff check src tests && mypy
inspect: ; npx @modelcontextprotocol/inspector learnloop
