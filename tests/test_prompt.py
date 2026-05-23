from pathlib import Path

from minicode.prompt import build_system_prompt


def test_build_system_prompt_includes_skills_and_mcp(tmp_path: Path) -> None:
    prompt = build_system_prompt(
        str(tmp_path),
        ["cwd: test"],
        {
            "skills": [{"name": "demo", "description": "demo skill"}],
            "mcpServers": [{"name": "fake", "status": "connected", "toolCount": 1, "resourceCount": 1, "promptCount": 1, "protocol": "newline-json"}],
        },
    )

    assert "Available skills:" in prompt
    assert "demo skill" in prompt
    assert "Configured MCP servers:" in prompt
    assert "fake: connected, tools=1" in prompt


def test_build_system_prompt_mentions_sequential_thinking_server(tmp_path: Path) -> None:
    prompt = build_system_prompt(
        str(tmp_path),
        [],
        {
            "mcpServers": [
                {"name": "SequentialThinking", "status": "connected", "toolCount": 1}
            ]
        },
    )

    assert "SEQUENTIAL THINKING MCP SERVER IS CONNECTED" in prompt
    assert "sequential_thinking" in prompt


def test_build_system_prompt_includes_memory_context(tmp_path: Path) -> None:
    prompt = build_system_prompt(
        str(tmp_path),
        [],
        {"memory_context": "# Project Memory\n\n- Always run pytest before release."},
    )

    assert "Project Memory & Context" in prompt
    assert "Always run pytest before release." in prompt


def test_build_system_prompt_routes_skills_to_bounded_candidates(tmp_path: Path) -> None:
    skills = [
        {
            "name": f"backend-{index}",
            "description": "database api migration workflow",
            "source": "test",
            "tags": ["backend", "database"],
            "intents": ["code"],
        }
        for index in range(8)
    ]
    skills.append(
        {
            "name": "frontend-dev",
            "description": "react ui dashboard workflow",
            "source": "test",
            "tags": ["frontend", "react", "ui"],
            "intents": ["code"],
        }
    )

    prompt = build_system_prompt(
        str(tmp_path),
        [],
        {
            "skills": skills,
            "skill_query": "Build a React dashboard UI",
        },
    )

    assert "frontend-dev" in prompt
    assert "backend-6" not in prompt
    assert "backend-7" not in prompt
    assert prompt.count("- backend-") <= 5
