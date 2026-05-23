# MiniCode Python

**A self-regulating Python coding agent for local development.**

[简体中文](./README.zh-CN.md) · [MiniCode Main Repo](https://github.com/LiuMengxuan04/MiniCode) · [Python Repo](https://github.com/QUSETIONS/MiniCode-Python)



MiniCode Python is the Python implementation in the MiniCode family. The main
project is [LiuMengxuan04/MiniCode](https://github.com/LiuMengxuan04/MiniCode);
this repository explores a Python-first agent runtime with cybernetic control,
adaptive memory, and a testable local tool loop.

Instead of treating context pressure, tool failures, memory noise, and cost
drift as prompt-only problems, MiniCode Python measures them during execution
and feeds those signals back into runtime decisions.

## Why It Exists

Most coding agents are model wrappers: prompt in, tool calls out, hope the loop
stays healthy. MiniCode Python is built around a different idea:

> a coding agent should observe itself while it works, then adjust its own
> context, memory, verification, concurrency, and recovery behavior.

That makes this repository useful as:

- a local coding-agent implementation you can inspect end to end;
- a Python research bed for agent control, memory, and verification loops;
- a companion implementation to the TypeScript MiniCode main repo;
- a practical place to test ideas before they become larger platform features.

## Highlights


| Area               | What MiniCode Python Adds                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| Runtime control    | `CyberneticOrchestrator` coordinates context, cost, feedback, progress, memory, and recovery controllers. |
| Context management | PID-style context pressure handling, compaction, budget adjustment, and predictive guards.                |
| Memory             | Domain-aware retrieval, optional LLM reranking, prompt injection, reflection write-back, and maintenance. |
| Tool loop          | Local file/search/edit/command tools with scheduler-aware execution and error nudges.                     |
| Recovery           | Self-healing paths for context overflow, tool failures, oscillation, and resource pressure.               |
| Verification       | Focused unit, integration, stress, and cybernetics tests across the active root package.                  |


## Architecture

```mermaid
flowchart LR
    User["User task"] --> Loop["agent_loop.py"]
    Loop --> Tools["Local tools<br/>files, search, edit, shell"]
    Tools --> Loop

    Loop --> Sensors["Sensors<br/>context, cost, errors, progress"]
    Sensors --> Orchestrator["CyberneticOrchestrator"]
    Orchestrator --> Control["Controllers<br/>PID, Kalman, prediction,<br/>memory, model, progress"]
    Control --> Actions["Runtime actions<br/>compact, cap concurrency,<br/>adjust budget, inject memory,<br/>recover, reflect"]
    Actions --> Loop
```



The main loop now drives the orchestrator lifecycle directly:

- `wire_memory()`
- `wire_healing()`
- `inject_memories()`
- `step_start()`
- `step_end()`
- `reflect_on_task()`

This keeps controller initialization, memory injection, per-step observation,
feedback, self-healing, and post-task reflection tied to the same runtime
surface.

## Repository Status

The active package is the root package configured in `pyproject.toml`.


| Path                           | Role                                                          |
| ------------------------------ | ------------------------------------------------------------- |
| `minicode/`                    | Canonical Python package used by install and tests.           |
| `tests/`                       | Active test suite.                                            |
| `py-src/minicode/`             | Compatibility/staging mirror kept aligned for migration work. |
| `docs/OPTIMIZATION_SUMMARY.md` | Full optimization and integration record.                     |
| `docs/memory_theory.md`        | Memory/control theory notes.                                  |


The main TypeScript repository may include this project as
`external/MiniCode-Python`, but this Python package is installed and verified
from this repository root.

## Quick Start

Recommended setup with `uv`:

```bash
python -m pip install --user uv
```

```bash
git clone https://github.com/iuiu-py/MiniCode-Python.git
cd MiniCode-Python
uv sync --extra dev
```

Run the CLI:

```bash
uv run minicode-py
```

Or run the module directly:

```bash
uv run python -m minicode.main
```

If you prefer plain `pip`, use an editable install:

```bash
python -m pip install -e ".[dev]"
```

Then run:

```bash
minicode-py
```

### Run From Any Directory

MiniCode uses the directory where you start the command as the workspace. To use
the current source checkout globally without reinstalling after normal code
changes, create a small launcher script:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/minicode-py <<'SH'
#!/usr/bin/env bash
exec uv run --project /home/zfwang/MiniCode minicode-py "$@"
SH
chmod +x ~/.local/bin/minicode-py
```

Make sure `~/.local/bin` is on your `PATH`, then run MiniCode from any project:

```bash
cd /path/to/your/project
minicode-py
```

This keeps `/home/zfwang/MiniCode` as the MiniCode source project while the
current directory remains the workspace that tools, memory, MCP config, and
permissions use.

Alternatively, install it as an editable `uv` tool:

```bash
uv tool install --editable /home/zfwang/MiniCode
uv tool update-shell
```

Editable tool installs usually pick up Python source changes after restarting
`minicode-py`; reinstall only when entry points, package metadata, or
dependencies change.

## Configuration

MiniCode reads configuration from `~/.mini-code/settings.json`, merged with
process environment variables. Environment variables take precedence, so you can
keep long-lived defaults in the settings file and override them per shell.

You can create the settings file manually:

```bash
mkdir -p ~/.mini-code
$EDITOR ~/.mini-code/settings.json
```

Keep real API keys out of committed files, screenshots, and shared logs.

Anthropic example:

```json
{
  "model": "claude-sonnet-4-20250514",
  "env": {
    "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
  }
}
```

OpenAI or OpenAI-compatible endpoint example:

```json
{
  "model": "gpt-4o",
  "env": {
    "OPENAI_API_KEY": "sk-...",
    "OPENAI_BASE_URL": "https://api.openai.com"
  }
}
```

For OpenAI-compatible proxies, `OPENAI_BASE_URL` may be either the provider root
or a versioned base URL:

```json
{
  "model": "gpt-4o",
  "env": {
    "OPENAI_API_KEY": "sk-...",
    "OPENAI_BASE_URL": "https://your-provider.example.com/v1"
  }
}
```

OpenRouter example:

```json
{
  "model": "anthropic/claude-sonnet-4",
  "env": {
    "OPENROUTER_API_KEY": "sk-or-...",
    "OPENROUTER_BASE_URL": "https://openrouter.ai/api"
  }
}
```

Custom OpenAI-compatible endpoint example:

```json
{
  "model": "my-local-model",
  "env": {
    "CUSTOM_API_KEY": "local-or-proxy-key",
    "CUSTOM_API_BASE_URL": "http://localhost:11434/v1"
  }
}
```

You can also use shell exports instead of a settings file:

```bash
export ANTHROPIC_MODEL=claude-sonnet-4-20250514
export ANTHROPIC_API_KEY=sk-ant-...
uv run minicode-py
```

## Verification

The current root package was verified with:

```bash
uv run python -m compileall -q minicode py-src/minicode tests
uv run pytest -q
```

Latest local result:

```text
738 passed, 2 skipped, 3 warnings
```

The warnings are unregistered `pytest.mark.benchmark` markers in benchmark
tests. They do not indicate failing behavior.

## Core Modules


| Module                                | Purpose                                               |
| ------------------------------------- | ----------------------------------------------------- |
| `minicode/agent_loop.py`              | Main model/tool loop and runtime control integration. |
| `minicode/cybernetic_orchestrator.py` | Facade for controller lifecycle hooks.                |
| `minicode/context_cybernetics.py`     | Context sensing, PID control, and compaction loop.    |
| `minicode/feedback_controller.py`     | Outer-loop system-state to control-signal mapping.    |
| `minicode/self_healing_engine.py`     | Fault detection and recovery delegation.              |
| `minicode/memory_pipeline.py`         | Unified memory read/inject/write/maintain facade.     |
| `minicode/memory_reranker.py`         | LLM-backed memory curation.                           |
| `minicode/domain_classifier.py`       | Task and file-domain inference.                       |
| `minicode/model_registry.py`          | Model selection controller.                           |
| `minicode/progress_controller.py`     | Task health and stall detection.                      |


## MiniCode Family


| Version    | Repository                                                                                                    | Focus                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| TypeScript | [LiuMengxuan04/MiniCode](https://github.com/LiuMengxuan04/MiniCode)                                           | Mainline terminal agent, TUI, MCP, skills, sessions, context controls.         |
| Python     | [QUSETIONS/MiniCode-Python](https://github.com/QUSETIONS/MiniCode-Python)                                     | Cybernetic Python runtime, memory pipeline, verification-oriented experiments. |
| Rust       | [harkerhand/MiniCode-rs](https://github.com/harkerhand/MiniCode-rs/tree/master)                               | Rust implementation and systems-side experimentation.                          |
| Java       | [hobbescalvin414-tech/minicode4j](https://github.com/hobbescalvin414-tech/minicode4j/tree/feat/default-ts-ui) | Java implementation with a TypeScript-style UI direction.                      |


## Documentation

- [Optimization Summary](./docs/OPTIMIZATION_SUMMARY.md)
- [Memory Theory](./docs/memory_theory.md)
- [Main MiniCode Repository](https://github.com/LiuMengxuan04/MiniCode)

## Design Principles

- Keep the agent loop inspectable.
- Prefer measured runtime signals over hidden prompt magic.
- Apply bounded actions: compact, cap, adjust, recover, reflect.
- Treat verification and evidence as part of the agent runtime.
- Keep the Python implementation useful as both software and research scaffold.

