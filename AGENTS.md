# AGENTS.md

Guidance for AI agents working in this repository.

## Project

从豆包（Doubao / Dola）对话分享链接中提取**无水印**图片和视频的 PySide6 桌面客户端。
仅支持豆包系，不支持千问。解析逻辑位于自包含的 `parser/` 包，界面位于 `app/` 包。
领域词汇见 `CONTEXT.md`。

## Agent skills

### Issue tracker

Issues and specs for this repo live as GitHub issues, operated via the `gh` CLI.
See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at the repo root plus `docs/adr/`.
See `docs/agents/domain.md`.

## Engineering workflow

- **Test-driven development** at pre-agreed seams. Tests live in `tests/` (pytest + pytest-asyncio).
- **Parser seams** (pure logic, no GUI): `parser/image.py`, `parser/video.py`, `parser/video_crypto.py`.
- Run `uv run pytest` for tests, `uv run ruff check .` for lint, `uv run ruff format .` for formatting.
- Do not commit unless asked.

## Commands

```bash
uv run python main.py        # run the desktop client
uv run pytest                # run tests
uv run ruff check .          # lint
uv run ruff format .         # format
```
