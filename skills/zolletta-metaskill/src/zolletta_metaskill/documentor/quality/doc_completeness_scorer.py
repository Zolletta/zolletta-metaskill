"""DocCompletenessScorer evaluates the structural completeness of documentation.

Checks whether expected sections (e.g. Diátaxis quadrants or README conventions)
are present in document files.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


class DocCompletenessScorer:
    """Scores documentation based on section completeness and structural requirements."""

    DIATAXIS_QUADRANTS: dict[str, dict[str, Any]] = {
        "tutorials": {
            "dir_names": {"tutorials", "tutorial"},
            "required_sections": ["what we will learn", "prerequisites"],
        },
        "how-to": {
            "dir_names": {"how-to", "howto", "how_to", "guides"},
            "any_of_groups": [["prerequisites", "before starting"]],
            "required_sections": [],
        },
        "reference": {
            "dir_names": {"reference", "ref"},
            "required_sections": [],
        },
        "explanation": {
            "dir_names": {"explanation", "explanations", "concepts"},
            "required_sections": [],
        },
    }

    @staticmethod
    def load_diataxis_translations(path: str) -> dict[str, Any]:
        """Load translated Diátaxis signposts from a JSON file."""
        try:
            with open(path, encoding="utf-8") as f:  # pragma: no mutate — equivalent on UTF-8
                data = json.load(f)
            if not isinstance(data, dict):
                return {"readme_sections": None, "quadrants": {}}
            readme_sections = data.get("readme_sections")
            quadrants = data.get("quadrants", data)
            return {"readme_sections": readme_sections, "quadrants": quadrants}
        except (OSError, json.JSONDecodeError):
            return {"readme_sections": None, "quadrants": {}}

    @staticmethod
    def merged_quadrants(translations: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Return ``DIATAXIS_QUADRANTS`` with *translations* applied.

        Pure: the class attribute is never mutated. A per-invocation settings
        value must not write into process-global state -- the previous
        ``merge_translations`` did exactly that, irreversibly, so a scoped or
        stale settings dict permanently altered the quadrant config for the rest
        of the process.

        Merge semantics are inherited from that implementation and are
        deliberately mixed: ``dir_names`` **unions** (additive), while
        ``required_sections`` and ``any_of_groups`` **replace**.

        Returns:
            A new quadrant mapping, safe for the caller to pass around.

        """
        merged: dict[str, dict[str, Any]] = {
            name: {
                key: DocCompletenessScorer._copy_quadrant_value(value)
                for key, value in quad.items()
            }
            for name, quad in DocCompletenessScorer.DIATAXIS_QUADRANTS.items()
        }
        quadrants = translations.get("quadrants", translations)
        for name, quad_trans in quadrants.items():
            if not isinstance(quad_trans, dict):
                continue
            quad = merged.setdefault(name, {"dir_names": set(), "required_sections": []})
            if "dir_names" in quad_trans and isinstance(quad_trans["dir_names"], list):
                quad["dir_names"] = set(quad["dir_names"]) | {
                    d.lower() for d in quad_trans["dir_names"]
                }
            if "required_sections" in quad_trans and isinstance(
                quad_trans["required_sections"], list
            ):
                quad["required_sections"] = [s.lower() for s in quad_trans["required_sections"]]
            if "any_of_groups" in quad_trans and isinstance(quad_trans["any_of_groups"], list):
                quad["any_of_groups"] = [
                    [s.lower() for s in group] for group in quad_trans["any_of_groups"]
                ]
        return merged

    @staticmethod
    def _copy_quadrant_value(value: Any) -> Any:
        """Copy one quadrant config value so the class attribute is never shared."""
        if isinstance(value, set):
            return set(value)
        if isinstance(value, list):
            return list(value)
        return value

    @staticmethod
    def detect_diataxis_quadrant(
        doc_path: str, quadrants: dict[str, dict[str, Any]] | None = None
    ) -> dict[str, Any] | None:
        """Return the Diátaxis quadrant config if the doc is inside a quadrant directory.

        Args:
            doc_path: Repo-relative path of the document.
            quadrants: Effective quadrant mapping, e.g. from
                :meth:`merged_quadrants`. Defaults to the built-in
                ``DIATAXIS_QUADRANTS``.

        """
        effective = quadrants if quadrants is not None else DocCompletenessScorer.DIATAXIS_QUADRANTS
        parts_lower = [p.lower() for p in Path(doc_path).parts]
        for quadrant in effective.values():
            if any(part in quadrant["dir_names"] for part in parts_lower):
                return quadrant
        return None

    @staticmethod
    def score_completeness(
        repo_path: str,
        doc_path: str,
        required_sections: list[str],
        quadrants: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score based on whether expected sections are present. 0-100.

        Args:
            repo_path: Absolute path to the repository root.
            doc_path: Repo-relative path of the document.
            required_sections: README sections to look for outside quadrants.
            quadrants: Effective Diátaxis quadrant mapping. Defaults to the
                built-in ``DIATAXIS_QUADRANTS``.

        """
        full_path = os.path.join(repo_path, doc_path)
        details: dict[str, Any] = {
            "expected_sections": required_sections,
            "found_sections": [],
            "missing_sections": [],
        }

        any_of_groups: list[list[str]] = []
        # pragma: no mutate start — arg mutants collapse to the same None default
        quadrant = DocCompletenessScorer.detect_diataxis_quadrant(doc_path, quadrants)
        # pragma: no mutate end
        if quadrant is not None:
            required_sections = quadrant.get("required_sections", [])
            any_of_groups = quadrant.get("any_of_groups", [])
            details["expected_sections"] = required_sections
            details["doc_structure"] = "diataxis"
            details["any_of_groups"] = any_of_groups

        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
                content = f.read()
        except OSError:
            return 0.0, details

        headings_lower = DocCompletenessScorer._collect_heading_text(content)
        heading_words: set[str] = set()
        for h in headings_lower:
            heading_words.update(h.split())

        found, missing = DocCompletenessScorer._match_sections(
            required_sections, headings_lower, heading_words
        )

        groups_found, groups_missing = DocCompletenessScorer._match_any_of_groups(
            any_of_groups, headings_lower, heading_words
        )

        details["found_sections"] = found
        details["missing_sections"] = missing
        details["any_of_groups_found"] = groups_found
        details["any_of_groups_missing"] = groups_missing

        is_diataxis = quadrant is not None
        content_lines = len([line for line in content.splitlines() if line.strip()])
        length_penalty = 0
        if not is_diataxis:
            if content_lines < 10:
                length_penalty = 30
            elif content_lines < 30:
                length_penalty = 15

        total_requirements = len(required_sections) + len(any_of_groups)
        if total_requirements == 0:
            # pragma: no mutate start — penalty ≤ 30, so the floor never binds
            return max(0.0, 100.0 - length_penalty), details
            # pragma: no mutate end

        satisfied = len(found) + groups_found
        section_score = (satisfied / total_requirements) * 100.0

        if section_score >= 100.0 and total_requirements > 1:
            length_penalty = 0

        return max(0.0, section_score - length_penalty), details

    @staticmethod
    def _collect_heading_text(content: str) -> set[str]:
        """Collect the lowercase text of every markdown heading (levels 1-4)."""
        headings_lower: set[str] = set()
        for line in content.splitlines():
            match = re.match(r"^#{1,4}\s+(.+)", line)
            if match:
                headings_lower.add(match.group(1).strip().lower())
        return headings_lower

    @staticmethod
    def _match_sections(
        required_sections: list[str],
        headings_lower: set[str],
        heading_words: set[str],
    ) -> tuple[list[str], list[str]]:
        """Split required sections into (found, missing) against the headings."""
        found = []
        missing = []
        for section in required_sections:
            section_lower = section.lower()
            # pragma: no mutate start — substring clause subsumes membership, flips are equivalent
            if (
                section_lower in headings_lower
                or section_lower in heading_words
                or any(section_lower in h for h in headings_lower)
            ):
                # pragma: no mutate end
                found.append(section)
            else:
                missing.append(section)
        return found, missing

    @staticmethod
    def _match_any_of_groups(
        any_of_groups: list[list[str]],
        headings_lower: set[str],
        heading_words: set[str],
    ) -> tuple[int, list[list[str]]]:
        """Count satisfied any-of groups; return (found_count, missing_groups)."""
        groups_found = 0
        groups_missing = []
        for group in any_of_groups:
            group_lower = [g.lower() for g in group]
            # pragma: no mutate start — substring any() subsumes membership, flips are equivalent
            if any(g in headings_lower or g in heading_words for g in group_lower) or any(
                any(g in h for h in headings_lower) for g in group_lower
            ):
                # pragma: no mutate end
                groups_found += 1
            else:
                groups_missing.append(group)
        return groups_found, groups_missing
