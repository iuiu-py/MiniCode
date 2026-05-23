from __future__ import annotations

import shutil
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from minicode.intent_parser import IntentType, ParsedIntent, parse_intent


class SkillLayer(str, Enum):
    ATOMIC_TOOL = "atomic_tool"
    WORKFLOW_SKILL = "workflow_skill"
    SKILL_DIRECTORY = "skill_directory"


@dataclass(slots=True)
class SkillMetadata:
    """Searchable skill metadata used by the routing layer."""

    layer: str = SkillLayer.WORKFLOW_SKILL.value
    tags: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    not_for: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SkillRouteMatch:
    skill: "SkillSummary"
    score: float
    stage: str
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SkillSummary:
    name: str
    description: str
    path: str
    source: str
    layer: str = SkillLayer.WORKFLOW_SKILL.value
    tags: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    not_for: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LoadedSkill(SkillSummary):
    content: str = ""


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_WORD_RE = re.compile(r"[\w\u4e00-\u9fff-]+", re.I)


def extract_description(markdown: str) -> str:
    _, markdown = _split_frontmatter(markdown)
    normalized = markdown.replace("\r\n", "\n")
    paragraphs = [block.strip() for block in normalized.split("\n\n") if block.strip()]
    for block in paragraphs:
        if block.startswith("#"):
            continue
        for line in [part.strip() for part in block.split("\n")]:
            if line and not line.startswith("#"):
                return line.replace("`", "")
    return "No description provided."


def _split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    return _parse_simple_frontmatter(match.group(1)), markdown[match.end():]


def _parse_simple_frontmatter(text: str) -> dict[str, Any]:
    """Parse a conservative YAML-like metadata block without dependencies."""
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") and current_key:
            value = line[1:].strip()
            if value:
                existing = data.setdefault(current_key, [])
                if isinstance(existing, list):
                    existing.append(_unquote(value))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower().replace("-", "_")
        value = value.strip()
        current_key = key
        if not value:
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [_unquote(part.strip()) for part in value[1:-1].split(",") if part.strip()]
        else:
            data[key] = _unquote(value)
    return data


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if "," in value:
            return [_normalize_token(part) for part in value.split(",") if _normalize_token(part)]
        normalized = _normalize_token(value)
        return [normalized] if normalized else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            normalized = _normalize_token(str(item))
            if normalized:
                result.append(normalized)
        return _unique(result)
    return []


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _section_lines(markdown: str, names: set[str]) -> list[str]:
    lines = markdown.replace("\r\n", "\n").splitlines()
    result: list[str] = []
    active = False
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            title = heading.group(2).strip().lower()
            active = any(name in title for name in names)
            continue
        if active:
            stripped = line.strip()
            if stripped:
                result.append(stripped.lstrip("-*0123456789. ").strip())
    return result


def _heading_terms(markdown: str) -> list[str]:
    return [_normalize_token(match.group(2)) for match in _HEADING_RE.finditer(markdown)]


def extract_skill_metadata(markdown: str, fallback_name: str = "") -> SkillMetadata:
    frontmatter, body = _split_frontmatter(markdown)
    tags = _as_list(frontmatter.get("tags"))
    intents = _as_list(frontmatter.get("intents") or frontmatter.get("intent"))
    applies_to = _as_list(
        frontmatter.get("applies_to")
        or frontmatter.get("applies")
        or frontmatter.get("use_when")
    )
    not_for = _as_list(
        frontmatter.get("not_for")
        or frontmatter.get("avoid_when")
        or frontmatter.get("out_of_scope")
    )
    examples = _as_list(frontmatter.get("examples"))
    tools = _as_list(frontmatter.get("tools"))

    tags.extend(_heading_terms(body))
    applies_to.extend(_section_lines(body, {"use when", "when to use", "applies", "适用", "使用场景"}))
    not_for.extend(_section_lines(body, {"do not use", "not for", "avoid", "边界", "不适用"}))
    examples.extend(_section_lines(body, {"example", "examples", "示例"}))

    description = extract_description(body)
    inferred_terms = _infer_terms(" ".join([fallback_name, description]))
    tags.extend(inferred_terms)
    intents.extend(_infer_intents(" ".join([fallback_name, description, " ".join(tags), " ".join(applies_to)])))

    layer = str(frontmatter.get("layer") or frontmatter.get("type") or SkillLayer.WORKFLOW_SKILL.value)
    layer = _normalize_token(layer)
    if layer in {"tool", "atomic", "atomic-tool"}:
        layer = SkillLayer.ATOMIC_TOOL.value
    elif layer in {"directory", "skill-directory", "category"}:
        layer = SkillLayer.SKILL_DIRECTORY.value
    else:
        layer = SkillLayer.WORKFLOW_SKILL.value

    return SkillMetadata(
        layer=layer,
        tags=_unique(tags)[:40],
        intents=_unique(intents)[:20],
        applies_to=_unique(applies_to)[:20],
        not_for=_unique(not_for)[:20],
        examples=_unique(examples)[:20],
        tools=_unique(tools)[:20],
    )


def _infer_terms(text: str) -> list[str]:
    words = [word.lower() for word in _WORD_RE.findall(text)]
    aliases = {
        "frontend": {"frontend", "react", "vue", "component", "page", "css", "ui"},
        "backend": {"backend", "api", "server", "database", "db", "endpoint"},
        "debug": {"debug", "bug", "error", "fail", "exception", "traceback", "调试"},
        "test": {"test", "tdd", "pytest", "unit", "integration", "测试"},
        "review": {"review", "audit", "inspect", "审查", "评审"},
        "plan": {"plan", "design", "architecture", "方案", "设计"},
        "document": {"doc", "docs", "readme", "documentation", "文档"},
        "refactor": {"refactor", "cleanup", "optimize", "重构", "优化"},
    }
    found = set(words)
    for canonical, group in aliases.items():
        if found & group:
            found.add(canonical)
    return sorted(found)[:40]


def _infer_intents(text: str) -> list[str]:
    terms = set(_infer_terms(text))
    mapping = {
        IntentType.DEBUG.value: {"debug", "bug", "error", "fail", "exception", "调试"},
        IntentType.TEST.value: {"test", "tdd", "pytest", "测试"},
        IntentType.REVIEW.value: {"review", "audit", "审查", "评审"},
        IntentType.DOCUMENT.value: {"document", "doc", "docs", "readme", "文档"},
        IntentType.REFACTOR.value: {"refactor", "optimize", "cleanup", "重构", "优化"},
        IntentType.CODE.value: {"code", "implement", "feature", "frontend", "backend", "component"},
    }
    return [intent for intent, hints in mapping.items() if terms & hints]


def _home_dir() -> Path:
    return Path.home()


def _skill_roots(cwd: str | Path) -> list[tuple[Path, str]]:
    base = Path(cwd)
    home = _home_dir()
    return [
        (base / ".mini-code" / "skills", "project"),
        (home / ".mini-code" / "skills", "user"),
        (base / ".claude" / "skills", "compat_project"),
        (home / ".claude" / "skills", "compat_user"),
    ]


def _list_skill_dirs(root: Path, source: str) -> list[LoadedSkill]:
    if not root.exists():
        return []
    results: list[LoadedSkill] = []
    for entry in root.iterdir():
        try:
            if not entry.is_dir():
                continue
        except OSError:
            # Windows: untrusted mount points, broken symlinks, etc.
            continue
        skill_path = entry / "SKILL.md"
        if not skill_path.exists():
            continue
        try:
            content = skill_path.read_text(encoding="utf-8")
        except OSError:
            continue
        metadata = extract_skill_metadata(content, fallback_name=entry.name)
        results.append(
            LoadedSkill(
                name=entry.name,
                description=extract_description(content),
                path=str(skill_path),
                source=source,
                layer=metadata.layer,
                tags=metadata.tags,
                intents=metadata.intents,
                applies_to=metadata.applies_to,
                not_for=metadata.not_for,
                examples=metadata.examples,
                tools=metadata.tools,
                content=content,
            )
        )
    return results


def discover_skills(cwd: str | Path) -> list[SkillSummary]:
    by_name: dict[str, LoadedSkill] = {}
    for root, source in _skill_roots(cwd):
        for skill in _list_skill_dirs(root, source):
            by_name.setdefault(skill.name, skill)
    return [
        SkillSummary(
            name=skill.name,
            description=skill.description,
            path=skill.path,
            source=skill.source,
            layer=skill.layer,
            tags=list(skill.tags),
            intents=list(skill.intents),
            applies_to=list(skill.applies_to),
            not_for=list(skill.not_for),
            examples=list(skill.examples),
            tools=list(skill.tools),
        )
        for skill in by_name.values()
    ]


def load_skill(cwd: str | Path, name: str) -> LoadedSkill | None:
    normalized_name = name.strip()
    if not normalized_name:
        return None
    for root, source in _skill_roots(cwd):
        skill_path = root / normalized_name / "SKILL.md"
        if skill_path.exists():
            content = skill_path.read_text(encoding="utf-8")
            metadata = extract_skill_metadata(content, fallback_name=normalized_name)
            return LoadedSkill(
                name=normalized_name,
                description=extract_description(content),
                path=str(skill_path),
                source=source,
                layer=metadata.layer,
                tags=metadata.tags,
                intents=metadata.intents,
                applies_to=metadata.applies_to,
                not_for=metadata.not_for,
                examples=metadata.examples,
                tools=metadata.tools,
                content=content,
            )
    return None


def route_skills(
    skills: list[SkillSummary] | list[dict[str, Any]],
    query: str,
    *,
    max_results: int = 6,
    recall_limit: int = 24,
    parsed_intent: ParsedIntent | None = None,
) -> list[SkillRouteMatch]:
    """Two-stage skill routing: broad directory/tag recall, then boundary-aware rerank."""
    normalized_query = query.strip()
    if not normalized_query:
        return [
            SkillRouteMatch(skill=_coerce_skill_summary(skill), score=0.0, stage="unrouted", reasons=["no query"])
            for skill in skills[:max_results]
        ]

    intent = parsed_intent or parse_intent(normalized_query)
    query_terms = set(_infer_terms(normalized_query))
    query_terms.update(_normalize_token(keyword) for keyword in intent.keywords)
    query_terms.update(_normalize_token(lang) for lang in intent.entities.get("languages", []))
    query_terms.discard("")

    recalled: list[SkillRouteMatch] = []
    for raw_skill in skills:
        skill = _coerce_skill_summary(raw_skill)
        score, reasons = _recall_score(skill, normalized_query, query_terms, intent)
        if score > 0:
            recalled.append(SkillRouteMatch(skill=skill, score=score, stage="recall", reasons=reasons))

    if not recalled:
        recalled = [
            SkillRouteMatch(skill=_coerce_skill_summary(skill), score=0.05, stage="fallback", reasons=["fallback"])
            for skill in skills[: min(max_results, len(skills))]
        ]

    recalled.sort(key=lambda item: item.score, reverse=True)
    reranked: list[SkillRouteMatch] = []
    for match in recalled[:recall_limit]:
        penalty, penalty_reasons = _boundary_penalty(match.skill, normalized_query, query_terms)
        bonus, bonus_reasons = _example_bonus(match.skill, normalized_query, query_terms)
        final = max(0.0, match.score + bonus - penalty)
        reasons = match.reasons + bonus_reasons + penalty_reasons
        if final > 0:
            reranked.append(SkillRouteMatch(match.skill, round(final, 4), "rerank", reasons=_unique(reasons)[:6]))

    reranked.sort(key=lambda item: (item.score, _layer_weight(item.skill.layer)), reverse=True)
    return reranked[:max_results]


def routed_skill_summaries(
    skills: list[SkillSummary] | list[dict[str, Any]],
    query: str,
    *,
    max_results: int = 6,
) -> list[dict[str, Any]]:
    matches = route_skills(skills, query, max_results=max_results)
    routed: list[dict[str, Any]] = []
    for match in matches:
        data = _skill_to_dict(match.skill)
        data["routeScore"] = match.score
        data["routeStage"] = match.stage
        data["routeReasons"] = match.reasons
        routed.append(data)
    return routed


def _recall_score(
    skill: SkillSummary,
    query: str,
    query_terms: set[str],
    intent: ParsedIntent,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    name = _normalize_token(skill.name)
    description = skill.description.lower()
    searchable = set(skill.tags) | set(skill.intents) | set(skill.applies_to) | set(skill.tools)

    if name and (name in query.lower() or name in query_terms):
        score += 4.0
        reasons.append("name")
    if intent.intent_type.value in skill.intents:
        score += 2.5
        reasons.append(f"intent:{intent.intent_type.value}")
    overlap = query_terms & searchable
    if overlap:
        score += min(3.0, len(overlap) * 0.6)
        reasons.append("tags:" + ",".join(sorted(overlap)[:3]))
    for term in query_terms:
        if term and term in description:
            score += 0.35
    for phrase in skill.applies_to:
        phrase_terms = set(_infer_terms(phrase))
        if phrase_terms and phrase_terms <= query_terms:
            score += 1.0
            reasons.append("boundary:applies")
    score += _layer_weight(skill.layer)
    return score, reasons


def _boundary_penalty(skill: SkillSummary, query: str, query_terms: set[str]) -> tuple[float, list[str]]:
    penalty = 0.0
    reasons: list[str] = []
    lowered_query = query.lower()
    for boundary in skill.not_for:
        boundary_terms = set(_infer_terms(boundary))
        if boundary and boundary.lower() in lowered_query:
            penalty += 4.0
            reasons.append("excluded:not_for")
        elif boundary_terms and boundary_terms <= query_terms:
            penalty += 2.0
            reasons.append("excluded:not_for")
    return penalty, reasons


def _example_bonus(skill: SkillSummary, query: str, query_terms: set[str]) -> tuple[float, list[str]]:
    bonus = 0.0
    reasons: list[str] = []
    lowered_query = query.lower()
    for example in skill.examples[:5]:
        example_terms = set(_infer_terms(example))
        if example and example.lower() in lowered_query:
            bonus += 1.5
            reasons.append("example")
        elif example_terms:
            overlap = query_terms & example_terms
            if overlap:
                bonus += min(1.0, len(overlap) * 0.25)
                reasons.append("example")
    return bonus, reasons


def _layer_weight(layer: str) -> float:
    if layer == SkillLayer.WORKFLOW_SKILL.value:
        return 0.25
    if layer == SkillLayer.SKILL_DIRECTORY.value:
        return 0.1
    if layer == SkillLayer.ATOMIC_TOOL.value:
        return 0.05
    return 0.0


def _coerce_skill_summary(skill: SkillSummary | dict[str, Any]) -> SkillSummary:
    if isinstance(skill, SkillSummary):
        return skill
    return SkillSummary(
        name=str(skill.get("name", "")),
        description=str(skill.get("description", "")),
        path=str(skill.get("path", "")),
        source=str(skill.get("source", "")),
        layer=str(skill.get("layer", SkillLayer.WORKFLOW_SKILL.value)),
        tags=list(skill.get("tags", []) or []),
        intents=list(skill.get("intents", []) or []),
        applies_to=list(skill.get("applies_to", []) or skill.get("appliesTo", []) or []),
        not_for=list(skill.get("not_for", []) or skill.get("notFor", []) or []),
        examples=list(skill.get("examples", []) or []),
        tools=list(skill.get("tools", []) or []),
    )


def _skill_to_dict(skill: SkillSummary) -> dict[str, Any]:
    return {
        "name": skill.name,
        "description": skill.description,
        "path": skill.path,
        "source": skill.source,
        "layer": skill.layer,
        "tags": list(skill.tags),
        "intents": list(skill.intents),
        "applies_to": list(skill.applies_to),
        "not_for": list(skill.not_for),
        "examples": list(skill.examples),
        "tools": list(skill.tools),
    }


def _managed_skill_root(scope: str, cwd: str | Path) -> Path:
    return (Path(cwd) / ".mini-code" / "skills") if scope == "project" else (_home_dir() / ".mini-code" / "skills")


def install_skill(cwd: str | Path, source_path: str, name: str | None = None, scope: str = "user") -> dict[str, str]:
    source = Path(source_path)
    if not source.is_absolute():
        source = Path(cwd) / source
    if source.is_dir():
        skill_file = source / "SKILL.md"
        inferred_name = source.name
    else:
        skill_file = source if source.name == "SKILL.md" else source / "SKILL.md"
        inferred_name = skill_file.parent.name
    if not skill_file.exists():
        raise RuntimeError(f"No SKILL.md found in {source}")

    skill_name = (name or inferred_name).strip()
    if not skill_name:
        raise RuntimeError("Skill name cannot be empty.")

    target_dir = _managed_skill_root(scope, cwd) / skill_name
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(skill_file, target_dir / "SKILL.md")
    return {"name": skill_name, "targetPath": str(target_dir / "SKILL.md")}


def remove_managed_skill(cwd: str | Path, name: str, scope: str = "user") -> dict[str, object]:
    target_path = _managed_skill_root(scope, cwd) / name
    if not target_path.exists():
        return {"removed": False, "targetPath": str(target_path)}
    shutil.rmtree(target_path)
    return {"removed": True, "targetPath": str(target_path)}
