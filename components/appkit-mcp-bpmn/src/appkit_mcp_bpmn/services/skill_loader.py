"""Utility for loading SKILL.md content."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_SKILL_PATH = Path(__file__).resolve().parent.parent / "resources" / "SKILL.md"


def load_skill_content() -> str:
    """Load the full SKILL.md content, stripping YAML frontmatter.

    Returns:
        The SKILL.md content without the opening frontmatter (--- ... ---).
        Returns empty string if the file is not found.
    """
    if not _SKILL_PATH.is_file():
        logger.warning("SKILL.md not found at %s", _SKILL_PATH)
        return ""

    try:
        content = _SKILL_PATH.read_text(encoding="utf-8")
        lines = content.split("\n")
        if lines and lines[0].startswith("---"):
            # Find the closing --- of the frontmatter
            for i, line in enumerate(lines[1:], 1):
                if line.startswith("---"):
                    # Skip to content after frontmatter
                    return "\n".join(lines[i + 1 :])
        return content
    except OSError as exc:
        logger.warning("Failed to read SKILL.md: %s", exc)
        return ""


def extract_skill_section(section_name: str) -> str:
    """Extract a specific section from SKILL.md by heading name.

    Args:
        section_name: The heading name to extract (e.g. "LLM System Prompt").

    Returns:
        The section content (without the heading), or empty string if not found.
    """
    if not _SKILL_PATH.is_file():
        logger.warning("SKILL.md not found at %s", _SKILL_PATH)
        return ""

    try:
        content = _SKILL_PATH.read_text(encoding="utf-8")
        # Find the section heading and extract until the next heading or EOF
        pattern = (
            rf"## {re.escape(section_name)}\s*\n"
            r"(.*?)"
            r"(?=\n## |\Z)"
        )
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        logger.debug("Section '%s' not found in SKILL.md", section_name)
        return ""
    except OSError as exc:
        logger.warning("Failed to read SKILL.md: %s", exc)
        return ""
