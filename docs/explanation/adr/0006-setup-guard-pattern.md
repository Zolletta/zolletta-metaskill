# ADR-0006: Setup guard pattern

## Status

Accepted

## Context

Every review subcommand depends on `settings.json` being present and up-to-date. Without it, subcommands would have to re-detect the project language, tool availability, and configuration on every invocation — slow, inconsistent, and fragile.

The alternative is to require users to run setup manually before any other subcommand. This is poor UX — users would hit errors on their first review because they forgot to run setup first.

## Decision

Every subcommand (including the orchestrator) runs a setup guard before executing its own logic:

1. If `settings.json` exists, read it and proceed to the requested subcommand.
2. If it does not exist, run the full setup procedure automatically, then proceed.
3. If the user invoked setup explicitly, run setup and stop — do not dispatch to another subcommand.
4. For Python projects: if `pyproject.toml` was modified after the last setup (comparing mtime against `python.pyproject_mtime`), re-run only the pyproject extraction step and patch the config fields. Do not re-run full setup.
5. For PHP projects: same staleness check against `composer.json` and `php.composer_mtime`.

This guarantees that every subcommand can assume `settings.json` is present and fresh without each one reimplementing detection logic.

## Consequences

**Positive:**

- Users can invoke any subcommand on a fresh project — setup runs automatically the first time.
- Subsequent invocations are fast because `settings.json` already exists.
- Staleness is handled with a light refresh (re-extract config), not a full re-setup (re-detect language, Docker, tokensave).
- The guard is centralized in the meta-skill, so subcommands do not duplicate the check.

**Negative:**

- The first invocation of any subcommand on a new project is slow (full setup runs). This is unavoidable — the information must be gathered once.
- The staleness check only covers pyproject.toml and composer.json. Other config drift (e.g., a new tool installed without a config file) is not detected until the next full setup.

**Neutral:**

- The setup guard is a convention enforced by the meta-skill's dispatch logic, not by code. Subcommands trust that `settings.json` is present because the guard runs before them.
