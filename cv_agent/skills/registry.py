from pathlib import Path

from cv_agent.skills.models import AgentSkill


ALLOWED_FIELDS = {
    "name",
    "description",
    "intent_examples",
    "allowed_categories",
    "allowed_sources",
    "output_rules",
    "network_access",
    "shell_access",
}
REQUIRED_FIELDS = ALLOWED_FIELDS
FORBIDDEN_MARKERS = ("http://", "https://", "sk-", "BEGIN PRIVATE KEY")


def _items(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split("|") if item.strip())


def _boolean(value: str, field: str) -> bool:
    normalized = value.lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"Booleano inválido en {field}")
    return normalized == "true"


def _load_skill(path: Path) -> AgentSkill:
    raw = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator or not value.strip():
            raise ValueError(f"Línea inválida en {path.name}: {line}")
        key = key.strip()
        if key not in ALLOWED_FIELDS:
            raise ValueError(f"Campo no permitido: {key}")
        values[key] = value.strip()
    if any(marker in raw for marker in FORBIDDEN_MARKERS):
        raise ValueError(f"Contenido inseguro en {path.name}")
    missing = REQUIRED_FIELDS - values.keys()
    if missing:
        raise ValueError(f"Faltan campos en {path.name}: {sorted(missing)}")
    network_access = _boolean(values["network_access"], "network_access")
    shell_access = _boolean(values["shell_access"], "shell_access")
    if network_access or shell_access:
        raise ValueError(f"Acceso ejecutable prohibido en {path.name}")
    sources = _items(values["allowed_sources"])
    if not sources or any(
        not source.startswith("knowledge/") or ".." in source
        for source in sources
    ):
        raise ValueError(f"Fuente no autorizada en {path.name}")
    return AgentSkill(
        name=values["name"],
        description=values["description"],
        intent_examples=_items(values["intent_examples"]),
        allowed_categories=_items(values["allowed_categories"]),
        allowed_sources=sources,
        output_rules=_items(values["output_rules"]),
        network_access=network_access,
        shell_access=shell_access,
    )


def load_skills(directory: Path | None = None) -> list[AgentSkill]:
    catalog = directory or Path(__file__).with_name("catalog")
    skills: list[AgentSkill] = []
    names: set[str] = set()
    for path in sorted(catalog.glob("*.yaml")):
        skill = _load_skill(path)
        if skill.name in names:
            raise ValueError(f"Skill duplicada: {skill.name}")
        names.add(skill.name)
        skills.append(skill)
    if not skills:
        raise ValueError(f"No hay skills en {catalog}")
    return skills
