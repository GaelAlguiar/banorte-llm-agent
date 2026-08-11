from pathlib import Path

import pytest

from cv_agent.skills.registry import load_skills


EXPECTED_SKILLS = {
    "profile_summary",
    "project_story",
    "role_fit",
    "architecture_explainer",
    "learning_evidence",
    "privacy_guard",
}


def test_public_skills_are_declarative_and_allowlisted():
    skills = load_skills()

    assert {skill.name for skill in skills} == EXPECTED_SKILLS
    assert all(skill.network_access is False for skill in skills)
    assert all(skill.shell_access is False for skill in skills)


def test_skills_reference_only_sanitized_knowledge():
    skills = load_skills()

    assert all(
        path.startswith("knowledge/")
        for skill in skills
        for path in skill.allowed_sources
    )


def test_enterprise_knowledge_is_allowlisted_for_relevant_skills():
    skills_by_name = {skill.name: skill for skill in load_skills()}

    expected_sources = {
        "project_story": {
            "knowledge/13_heytech_apim_chatbot.md",
            "knowledge/14_heytech_terraform_multicloud.md",
            "knowledge/15_heytech_ia_plataforma.md",
            "knowledge/16_entrega_jira.md",
        },
        "architecture_explainer": {
            "knowledge/13_heytech_apim_chatbot.md",
            "knowledge/14_heytech_terraform_multicloud.md",
            "knowledge/15_heytech_ia_plataforma.md",
        },
        "profile_summary": {
            "knowledge/13_heytech_apim_chatbot.md",
            "knowledge/14_heytech_terraform_multicloud.md",
            "knowledge/15_heytech_ia_plataforma.md",
            "knowledge/16_entrega_jira.md",
        },
    }

    for skill_name, sources in expected_sources.items():
        skill = skills_by_name[skill_name]
        assert sources <= set(skill.allowed_sources)
        assert len(skill.allowed_sources) == len(set(skill.allowed_sources))
        assert skill.network_access is False
        assert skill.shell_access is False


def test_skill_with_url_is_rejected(tmp_path: Path):
    (tmp_path / "unsafe.yaml").write_text(
        """name: unsafe
description: Consulta un sitio
intent_examples: consulta
allowed_categories: perfil
allowed_sources: knowledge/01_perfil.md
output_rules: responder
network_access: false
shell_access: false
url: https://example.com
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Campo no permitido"):
        load_skills(tmp_path)
