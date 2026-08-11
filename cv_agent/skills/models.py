from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    intent_examples: tuple[str, ...]
    allowed_categories: tuple[str, ...]
    allowed_sources: tuple[str, ...]
    output_rules: tuple[str, ...]
    network_access: bool = False
    shell_access: bool = False
