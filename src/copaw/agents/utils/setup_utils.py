# -*- coding: utf-8 -*-
"""Setup and initialization utilities for agent configuration.

This module handles copying markdown configuration files to
the working directory.
"""
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def md_files_base_dir() -> Path:
    """Root directory containing language/template markdown trees."""
    return Path(__file__).parent.parent / "md_files"


def resolve_language_subdir(language: str) -> Path:
    """Return `{md_files}/{language}` or fall back to `en`."""
    base = md_files_base_dir()
    lang_dir = base / language
    if not lang_dir.exists():
        logger.warning(
            "MD files directory not found: %s, falling back to 'en'",
            lang_dir,
        )
        lang_dir = base / "en"
    return lang_dir


def collect_md_files_for_template(
    language: str,
    template_id: str,
) -> dict[str, Path]:
    """Merge template markdown: `general/` base, language root gaps, then template overlay.

    Resolution order (later wins):
    1. ``{lang}/general/*.md``
    2. ``{lang}/*.md`` (root; only fills filenames missing from step 1)
    3. ``{lang}/{template_id}/*.md`` (overrides)
    """
    lang_dir = resolve_language_subdir(language)
    files: dict[str, Path] = {}

    general_dir = lang_dir / "general"
    if general_dir.is_dir():
        for md_file in sorted(general_dir.glob("*.md")):
            files[md_file.name] = md_file

    for md_file in sorted(lang_dir.glob("*.md")):
        files.setdefault(md_file.name, md_file)

    template_dir = lang_dir / template_id
    if template_dir.is_dir():
        for md_file in sorted(template_dir.glob("*.md")):
            files[md_file.name] = md_file

    return files


def copy_md_files(
    language: str,
    skip_existing: bool = False,
    workspace_dir: Path | None = None,
    template_id: str = "general",
) -> list[str]:
    """Copy md files from agents/md_files to working directory.

    Args:
        language: Language code (e.g. 'en', 'zh')
        skip_existing: If True, skip files that already exist in working dir.
        workspace_dir: Target workspace directory. If None, uses WORKING_DIR.
        template_id: Agent template id; selects overlay under ``md_files/{lang}/{template_id}/``.

    Returns:
        List of copied file names.
    """
    from ...constant import WORKING_DIR

    # Use provided workspace_dir or default to WORKING_DIR
    target_dir = workspace_dir if workspace_dir is not None else WORKING_DIR

    file_map = collect_md_files_for_template(language, template_id)
    if not file_map:
        logger.error("No md template files resolved for language=%s", language)
        return []

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    for name, md_file in sorted(file_map.items()):
        target_file = target_dir / name
        if skip_existing and target_file.exists():
            logger.debug("Skipped existing md file: %s", name)
            continue
        try:
            shutil.copy2(md_file, target_file)
            logger.debug("Copied md file: %s", name)
            copied_files.append(name)
        except Exception as e:
            logger.error(
                "Failed to copy md file '%s': %s",
                name,
                e,
            )

    if copied_files:
        logger.debug(
            "Copied %d md file(s) [%s] template=%s to %s",
            len(copied_files),
            language,
            template_id,
            target_dir,
        )

    return copied_files
