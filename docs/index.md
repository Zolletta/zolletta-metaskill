---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-*]
---

![zolletta-metaskill](../assets/zolletta-meta-skill-192.png)

A family of generic code review skills with specializations for Python and PHP (other languages in progress).

_Zolletta_ is Italian for sugar cubes — each skill is a compact, self-contained piece that sweetens the review process. Together they dissolve into a complete picture.

Zolletta-metaskill is a **meta-skill**: it dispatches to subcommands that each perform a specific review task. It leverages [tokensave](https://github.com/aovestdipaperino/tokensave) when available for semantic code-graph queries, and falls back to grep + targeted reads otherwise.

If you maintain rules as part of your agent configuration, those are the single source of truth for their domain and apply to every subcommand. Sub-skills link back to them and only narrow behavior for their specific review context. Zolletta-metaskill **complements** your rules — it does not override them.

## What it does

It runs as an AI agent skill inside tools like Claude Code, Cursor, Devin, and Windsurf, and reviews code for:

- **Design patterns** — SOLID violations, God classes, coupling, composition vs inheritance
- **Code style** — naming, typing, docstrings, linting (ruff, mypy, ty, PHPStan, Psalm)
- **Testing style** — test isolation, naming, coverage gaps, mocking patterns
- **Documentation** — Diátaxis compliance, drift detection, API validation
- **Architecture** — ADR distillation, external-LLM review of modified files

## Installation

```bash
git clone https://github.com/Zolletta/zolletta-metaskill.git
cd zolletta-metaskill
./install.sh
```

The `install.sh` script copies the skill to `~/.agents/skills/zolletta-metaskill` and symlinks it into every detected AI agent tool's skills directory (Claude Code, Cursor, Gemini CLI, Devin, Windsurf, and others). See the [install guide](https://metaskill.zolletta.org/how-to/install/) for details and manual alternatives.

## Try it out

After installation, navigate to a project and run a full review:

```text
cd /path/to/your/project
/zolletta-metaskill review
```

The first time you run any subcommand in a project, the **setup guard** automatically runs `/zolletta-metaskill setup` if `.zolletta-metaskill/settings.json` does not exist.

The orchestrator detects the language, runs all applicable skills in parallel, and writes reports to `.zolletta-metaskill/<timestamp>/reports/`. Start with `SUMMARY.md` for the overall grade and `TODO.md` for prioritized action items.

For a focused review, run a single subcommand:

```text
/zolletta-metaskill patterns          # God classes and SOLID
/zolletta-metaskill documentor        # documentation review
/zolletta-metaskill python-code-style # Python style only
```

New to Zolletta-metaskill? Read the [getting started tutorial](https://metaskill.zolletta.org/tutorials/getting-started/).

## Contributing

See [CONTRIBUTING.md](https://github.com/Zolletta/zolletta-metaskill/blob/main/CONTRIBUTING.md) for development setup, testing, and the quality gate.

## License

MIT + Commons Clause. See [LICENSE](https://github.com/Zolletta/zolletta-metaskill/blob/main/LICENSE) and the `license` field in each subcommand's `SKILL.md` frontmatter.

## Attributions

- **[wshobson/agents](https://github.com/wshobson/agents)** (MIT, Copyright (c) 2024 Seth Hobson) — `python-code-style` and `python-testing-style` skills adapted from the original Python review agents. Design pattern principles in `patterns` also adapted from wshobson's python-design-patterns
- **[Diátaxis Documentation Expert](https://github.com/github/awesome-copilot/blob/main/skills/documentation-writer/SKILL.md)** (MIT, github/awesome-copilot) — `documentor` skill derived from this documentation review skill
- **[Doc Drift Detector](https://github.com/borghei/Claude-Skills/blob/main/engineering/doc-drift-detector/SKILL.md)** (MIT + Commons Clause, borghei/Claude-Skills) — drift detection pipeline in `documentor` derived from this skill
- **[Diátaxis](https://diataxis.fr/)** — documentation framework used by the `documentor` subcommand for structure compliance checks
- **[tokensave](https://github.com/aovestdipaperino/tokensave)** — semantic code-graph MCP server leveraged for code exploration when available
- **[Architectural Governance at AI Speed](https://www.infoq.com/articles/architectural-governance-ai-speed/)** (InfoQ, 2026) — ADR distiller design inspired by this article's declarative architectural governance approach
