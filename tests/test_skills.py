from pathlib import Path

from minicode.skills import discover_skills, load_skill, route_skills


def test_discover_skills_prefers_project_root(tmp_path: Path, monkeypatch) -> None:
    project_skill = tmp_path / ".mini-code" / "skills" / "demo" / "SKILL.md"
    project_skill.parent.mkdir(parents=True)
    project_skill.write_text("# Demo\n\nProject description\n", encoding="utf-8")

    user_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(user_home))
    monkeypatch.setenv("USERPROFILE", str(user_home))
    user_skill = user_home / ".mini-code" / "skills" / "demo" / "SKILL.md"
    user_skill.parent.mkdir(parents=True)
    user_skill.write_text("# Demo\n\nUser description\n", encoding="utf-8")

    skills = discover_skills(tmp_path)

    assert len(skills) == 1
    assert skills[0].description == "Project description"
    loaded = load_skill(tmp_path, "demo")
    assert loaded is not None
    assert loaded.content.startswith("# Demo")


def test_discover_skills_extracts_routing_metadata(tmp_path: Path) -> None:
    skill_file = tmp_path / ".mini-code" / "skills" / "frontend-dev" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        """---
layer: workflow_skill
tags: [frontend, react, ui]
intents: [code, refactor]
applies_to:
  - Build React components and pages
not_for:
  - Backend database migrations
examples:
  - Rebuild a product dashboard in React
tools: [read_file, edit_file]
---

# Frontend Dev

Use this for polished UI implementation.
""",
        encoding="utf-8",
    )

    skills = discover_skills(tmp_path)

    assert len(skills) == 1
    assert skills[0].description == "Use this for polished UI implementation."
    assert skills[0].layer == "workflow_skill"
    assert "frontend" in skills[0].tags
    assert "code" in skills[0].intents
    assert "read-file" in skills[0].tools


def test_route_skills_uses_two_stage_metadata_and_boundaries(tmp_path: Path) -> None:
    frontend = tmp_path / ".mini-code" / "skills" / "frontend-dev" / "SKILL.md"
    backend = tmp_path / ".mini-code" / "skills" / "backend-dev" / "SKILL.md"
    frontend.parent.mkdir(parents=True)
    backend.parent.mkdir(parents=True)
    frontend.write_text(
        """---
tags: [frontend, react, ui]
intents: [code]
not_for: [backend database migration]
examples: [Build a React dashboard]
---

# Frontend Dev

Build components, pages, and browser UI.
""",
        encoding="utf-8",
    )
    backend.write_text(
        """---
tags: [backend, database, api]
intents: [code]
not_for: [react ui]
examples: [Add a database migration]
---

# Backend Dev

Build APIs and database workflows.
""",
        encoding="utf-8",
    )

    skills = discover_skills(tmp_path)
    matches = route_skills(skills, "Build a React dashboard UI", max_results=2)

    assert [match.skill.name for match in matches][0] == "frontend-dev"
    assert matches[0].score > matches[1].score
