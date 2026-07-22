# Plan: PHP Code Style Skill & Frontmatter Restructuring

## Goal

Extend zolletta-metaskill with a native `php-code-style` skill based on the 51 rules from the external `php-best-practices` skill (MIT, v2.1.0, by php-community), adapted to zolletta-metaskill's architecture:

- **8 rules already covered** by existing zolletta-metaskill scanners/docs → eliminated (no duplication).
- **10 rules are language-agnostic** in nature → promoted to 3 new general explanation docs (error-handling, performance, security) with both PHP and Python examples.
- **33 rules are PHP-specific** → confined to the new `php-code-style/` skill, version-gated by detected `php_version`.

Additionally:

- **Suggest `php-pro`** (MIT, v1.1.0, by Jeffallan) as a companion implementation skill when a PHP project is detected. php-pro is an implementation skill (writes PHP 8.3+ code, Laravel/Symfony, PHPUnit/Pest, PHPStan level 9), not a review skill — zolletta-metaskill can only suggest installing it, not integrate it into the review workflow.
- **Search for a Python equivalent** of php-pro on skills.sh and, if found, add a parallel suggestion for Python projects.
- **Restructure frontmatter** to support `python-*` and `php-*` wildcards in the `skills:` field, so language-specific skills don't need to be listed individually.

## Relationship to PLAN-PHP-SUPPORT.md

This plan **supersedes Phase 5.1** of `PLAN-PHP-SUPPORT.md` (which described a generic `php-code-style/` skill with a placeholder rule list). The detailed 33-rule set here replaces the placeholder. All other phases of `PLAN-PHP-SUPPORT.md` (common infrastructure, engines, scanner refactoring, PHP setup, SOLID scanners, docs, dependencies) remain unchanged and are prerequisites for the automated scanner portions of this plan.

## File ownership (shared with PLAN-PHP-SUPPORT.md)

Both this plan and PLAN-PHP-SUPPORT.md modify shared files. The table below assigns each file to exactly one plan to prevent conflicts. See [PLAN-MASTER.md](PLAN-MASTER.md) for the full orchestration.

| File | Owned by | Phase | Rationale |
| --- | --- | --- | --- |
| `setup/SKILL.md` (PHP detection) | PLAN-PHP-SUPPORT | Phase 4 | Has the detailed 9-step detection path |
| `setup/assets/settings_template.json` | PLAN-PHP-SUPPORT | Phase 4.6 | Already done (`"php": null` present) |
| `setup/assets/settings.schema.json` | PLAN-PHP-SUPPORT | Phase 4.8 | Needs `php.code_style` toggle fix (3→12) |
| `docs/reference/settings-schema.md` | PLAN-PHP-SUPPORT | Phase 4.9 | Has the detailed section list |
| `review/SKILL.md` (PHP rows) | This plan | Phase 4.3 | Has the detailed scope table |
| `SKILL.md` (root, PHP subcommands) | This plan | Phase 4.4 | Has the specific changes |
| `docs/reference/tool-messages.md` | This plan | Phase 1.2 | php-pro message |
| `docs/reference/frontmatter.md` | This plan | Phase 0.1 | Wildcard syntax |
| `PLAN-PHP-SUPPORT.md` (mark 5.1) | This plan | Phase 4.6 | Superseded marking |

## Rule classification (51 → 43 new rules)

### Already covered by zolletta-metaskill (8 rules — eliminated)

| Rule | php-best-practices ID | Covered by |
| --- | --- | --- |
| Single Responsibility | `solid-srp` | `patterns/` SOLID scanners + `general-principles.md` |
| Open/Closed | `solid-ocp` | `patterns/` SOLID scanners + `general-principles.md` |
| Liskov Substitution | `solid-lsp` | `patterns/` SOLID scanners + `general-principles.md` |
| Interface Segregation | `solid-isp` | `patterns/` SOLID scanners + `general-principles.md` |
| Dependency Inversion | `solid-dip` | `patterns/` SOLID scanners + `general-principles.md` |
| One class per file | `psr-file-structure` | `shared/scan_one_class_per_file.py` + `structural-conventions.md` |
| Class naming conventions | `psr-naming-classes` | `shared/scan_naming_conventions.py` + `structural-conventions.md` |
| Avoid global variables | `perf-avoid-globals` | `patterns/scan_dependency_inversion.py` (DIP covers this) |

### Promoted to language-agnostic docs (10 rules — 3 new files)

| Rule | php-best-practices ID | New doc | Why general |
| --- | --- | --- | --- |
| Custom exceptions | `error-custom-exceptions` | `error-handling.md` | Applies to Python, PHP, Java, etc. |
| Exception hierarchy | `error-exception-hierarchy` | `error-handling.md` | Language-agnostic pattern |
| Catch specific exceptions | `error-try-catch-specific` | `error-handling.md` | Same principle in Python |
| Finally for cleanup | `error-finally-cleanup` | `error-handling.md` | Universal construct |
| Lazy loading | `perf-lazy-loading` | `performance.md` | Applies to any language |
| Generators | `perf-generators` | `performance.md` | Python has `yield`, PHP has `yield` |
| Input validation | `sec-input-validation` | `security.md` | Security is language-agnostic |
| Output escaping | `sec-output-escaping` | `security.md` | XSS prevention applies everywhere |
| Password hashing | `sec-password-hashing` | `security.md` | Universal security practice |
| SQL prepared statements | `sec-sql-prepared` | `security.md` | Applies to any language with SQL |

### PHP-specific (33 rules — new php-code-style/ skill)

| Category | Count | Rules |
| --- | --- | --- |
| Type System | 9 | `type-strict-mode`, `type-return-types`, `type-parameter-types`, `type-property-types`, `type-union-types`, `type-intersection-types`, `type-nullable-types`, `type-void-never`, `type-mixed-avoid` |
| Modern PHP Features | 16 | `modern-constructor-promotion`, `modern-match-expression`, `modern-named-arguments`, `modern-nullsafe-operator`, `modern-attributes`, `modern-enums`, `modern-enums-methods`, `modern-readonly-properties`, `modern-first-class-callables`, `modern-arrow-functions`, `modern-readonly-classes`, `modern-typed-constants`, `modern-override-attribute`, `modern-property-hooks`, `modern-asymmetric-visibility`, `modern-pipe-operator` |
| PSR Standards | 4 | `psr-4-autoloading`, `psr-12-coding-style`, `psr-naming-methods`, `psr-namespace-usage` |
| Error Handling | 1 | `error-never-suppress` (PHP `@` operator — PHP-specific) |
| Performance | 2 | `perf-array-functions`, `perf-string-functions` (PHP-specific native functions) |
| Security | 1 | `sec-file-uploads` (PHP-specific `$_FILES` handling) |

---

## Phase 0 — Frontmatter restructuring

### 0.1 Update `docs/reference/frontmatter.md`

Document wildcard syntax for the `skills:` field:

- `python-*` — matches all Python-specific skills (`python-code-style`, `python-testing-patterns`, and any future Python skills)
- `php-*` — matches all PHP-specific skills (`php-code-style`, `php-testing-patterns`, and any future PHP skills)
- Wildcards are **preferred** for language-specific skills; explicit names are still allowed for files that target a single skill only.

Update the "Valid skill names" list to show both explicit names and wildcards. Add a note: "When a new language-specific skill is added, no docs files need updating if they already use the wildcard."

### 0.2 Update 13 docs files

Replace `python-code-style, python-testing-patterns` with `python-*` in the `skills:` frontmatter field of:

| File | Current `skills:` value | New `skills:` value |
| --- | --- | --- |
| `docs/index.md` | `[setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]` | `[setup, review, patterns, documentor, external-review, python-*]` |
| `docs/reference/subcommands.md` | same full list | `[setup, review, patterns, documentor, external-review, python-*]` |
| `docs/reference/frontmatter.md` (line 4) | same full list | `[setup, review, patterns, documentor, external-review, python-*]` |
| `docs/tutorials/getting-started.md` | same full list | `[setup, review, patterns, documentor, external-review, python-*]` |
| `docs/reference/code/tokensave.md` | `[patterns, documentor, review, external-review, python-code-style, python-testing-patterns]` | `[patterns, documentor, review, external-review, python-*]` |
| `docs/reference/code/review-mode.md` | `[review, python-code-style, python-testing-patterns]` | `[review, python-*]` |
| `docs/explanation/code/structural-conventions.md` | `[patterns, review, python-code-style, python-testing-patterns]` | `[patterns, review, python-*]` |
| `docs/explanation/code/python/python-review-patterns.md` | `[patterns, python-code-style, python-testing-patterns]` | `[patterns, python-*]` |
| `docs/how-to/code/review-test-code.md` | `[python-testing-patterns, review]` | `[python-*, review]` |
| `docs/how-to/code/review-code-style.md` | `[python-code-style, review]` | `[python-*, review]` |
| `docs/how-to/code/python/review-python-tests.md` | `[python-testing-patterns]` | `[python-*]` |
| `docs/how-to/code/python/review-python-style.md` | `[python-code-style]` | `[python-*]` |
| `docs/reference/code/python/python-code-style.md` | `[python-code-style, python-testing-patterns, review, patterns]` | `[python-*, review, patterns]` |

---

## Phase 1 — php-pro suggestion + Python equivalent search

### 1.1 Search skills.sh for Python equivalent of php-pro

Run `npx skills find python` and `npx skills find "python development"`. Evaluate candidates by:

- Install count (prefer 1K+)
- Source reputation (official orgs, known authors)
- Whether it's an implementation skill (writes code) vs. review skill

If a suitable Python implementation skill is found, add a parallel "not installed" message (Step 1.3) and detection step (Step 1.4) for Python projects. If not found, note it as a gap and move on.

### 1.2 Add php-pro "not installed" message to `docs/reference/tool-messages.md`

Add a new section after the existing tool messages:

```text
ℹ php-pro is not installed.

php-pro is a companion implementation skill for PHP projects. It writes
PHP 8.3+ code with strict typing, Laravel/Symfony patterns, PHPUnit/Pest
tests, and PHPStan level 9 verification. Zolletta-metaskill is a review
skill — it checks code quality but does not write code. For projects
that need PHP code generation alongside review, install php-pro:

  npx skills add jeffallan/claude-skills@php-pro -g -y

Homepage: https://skills.sh/jeffallan/claude-skills/php-pro
```

### 1.3 Add php-pro detection to `setup/SKILL.md`

Add to the PHP tooling detection step (from PLAN-PHP-SUPPORT.md Phase 4):

- Check if `~/.agents/skills/php-pro/SKILL.md` exists
- Store `php.tools.php_pro_available` boolean in `settings.json`
- If not available, print the "not installed" message from Step 1.2

---

## Phase 2 — Language-agnostic explanation docs (10 promoted rules)

### 2.1 Create `docs/explanation/code/error-handling.md`

4 rules with PHP + Python examples:

1. **Custom exceptions** — create specific exception classes instead of using generic base exceptions
2. **Exception hierarchy** — organize exceptions into a meaningful hierarchy (domain → subdomain → specific)
3. **Catch specific exceptions** — catch specific exception types, not the generic base class
4. **Finally for cleanup** — use `finally` for guaranteed resource cleanup

Frontmatter: `skills: [patterns, review, python-*, php-*]`

### 2.2 Create `docs/explanation/code/performance.md`

2 rules with PHP + Python examples:

1. **Lazy loading** — defer expensive operations until actually needed (PHP: lazy initialization, Python: `functools.lru_cache`, `@cached_property`)
2. **Generators** — use generators for large datasets (PHP: `yield`, Python: `yield` / generator expressions)

Frontmatter: `skills: [patterns, review, python-*, php-*]`

### 2.3 Create `docs/explanation/code/security.md`

4 rules with PHP + Python examples:

1. **Input validation** — validate and sanitize all external input; whitelist over blacklist
2. **Output escaping** — escape output based on context (HTML, JS, URL, CSS)
3. **Password hashing** — use `password_hash`/`password_verify` (PHP) or `bcrypt`/`argon2` (Python); never MD5/SHA1
4. **SQL prepared statements** — use parameterized queries for all SQL (PHP: PDO prepared, Python: DB-API parameterization)

Frontmatter: `skills: [patterns, review, python-*, php-*]`

### 2.4 Update `docs/index.md`

Add 3 new rows to the "Code review principles" table in the Explanation quadrant:

| Document | Description |
| --- | --- |
| [Error handling](explanation/code/error-handling.md) | Custom exceptions, hierarchy, specific catch, finally cleanup |
| [Performance](explanation/code/performance.md) | Lazy loading, generators for large datasets |
| [Security](explanation/code/security.md) | Input validation, output escaping, password hashing, SQL prepared statements |

---

## Phase 3 — php-code-style skill (33 PHP-specific rules)

### 3.1 Create `php-code-style/SKILL.md`

Structure mirrors `python-code-style/SKILL.md`:

- Frontmatter: `name: php-code-style`, `version: 1.3.0`, `license: MIT + Commons Clause`
- Configuration source: reads `php.tools.*`, `php.code_style`, `php.php_version` from `settings.json`
- Review mode: links to `docs/reference/code/review-mode.md`
- Two rule tables: **Always-on** (cannot be disabled) and **Configurable** (stored in `settings.json` under `php.code_style`)

#### Always-on rules (21)

| #   | Area     | Name                                                       | Min PHP version |
| --- | -------- | ---------------------------------------------------------- | --------------- |
| 1   | Types    | `declare(strict_types=1)` in every file                    | 7.0+            |
| 2   | Types    | Return type declarations on all methods                    | 7.0+            |
| 3   | Types    | Parameter type declarations                                | 7.0+            |
| 4   | Types    | Property type declarations                                 | 7.4+            |
| 5   | Types    | Nullable types explicitly declared                         | 7.1+            |
| 6   | Types    | Use `void`/`never` for appropriate returns                 | 8.1+ (never)    |
| 7   | Types    | Avoid `mixed` when a specific type is possible             | 8.0+            |
| 8   | Modern   | Constructor property promotion                             | 8.0+            |
| 9   | Modern   | Match expression over switch                               | 8.0+            |
| 10  | Modern   | Nullsafe operator for null chains                          | 8.0+            |
| 11  | Modern   | Named arguments for clarity                                | 8.0+            |
| 12  | Modern   | Attributes for metadata (not docblocks)                    | 8.0+            |
| 13  | Modern   | Enums instead of class constants for finite sets           | 8.1+            |
| 14  | Modern   | Readonly properties for immutable data                     | 8.1+            |
| 15  | Modern   | Arrow functions for short closures                         | 7.4+            |
| 16  | PSR      | PSR-4 autoloading compliance                               | all             |
| 17  | PSR      | PSR-12 coding style compliance                             | all             |
| 18  | PSR      | camelCase method names                                     | all             |
| 19  | PSR      | Proper namespace usage                                     | all             |
| 20  | Error    | Never use `@` error suppression operator                   | all             |
| 21  | Security | Validate file uploads (type, size, name, storage location) | all             |

#### Configurable rules (12, version-gated)

| # | Area | Name | Key | Default | Min PHP |
| --- | --- | --- | --- | --- | --- |
| 22 | Types | Union types | `check_union_types` | `true` | 8.0+ |
| 23 | Types | Intersection types | `check_intersection_types` | `true` | 8.1+ |
| 24 | Modern | Enums with methods | `check_enum_methods` | `true` | 8.1+ |
| 25 | Modern | First-class callable syntax | `check_first_class_callables` | `true` | 8.1+ |
| 26 | Modern | Readonly classes | `check_readonly_classes` | `true` | 8.2+ |
| 27 | Modern | Typed class constants | `check_typed_constants` | `true` | 8.3+ |
| 28 | Modern | `#[\Override]` attribute | `check_override_attribute` | `true` | 8.3+ |
| 29 | Modern | Property hooks | `check_property_hooks` | `true` | 8.4+ |
| 30 | Modern | Asymmetric visibility | `check_asymmetric_visibility` | `true` | 8.4+ |
| 31 | Modern | Pipe operator | `check_pipe_operator` | `true` | 8.5+ |
| 32 | Perf | Use native array functions over manual loops | `check_array_functions` | `true` | all |
| 33 | Perf | Use native string functions over regex | `check_string_functions` | `true` | all |

**Version gating**: rules whose min PHP version is higher than the detected `php_version` are silently skipped (not flagged). The skill prints a note: "Rules #X–#Y skipped (require PHP 8.N+, project targets 8.M)."

### 3.2 Create `php-code-style/assets/report_template.md`

Report template matching `patterns/assets/report_template.md` format:

- Header: project name, language, scan date, generated by
- Grade section (score + justification)
- Tool results section (PHPStan, PHPCS, php-cs-fixer output if available)
- Findings by severity (Critical, High, Medium, Low) — same table format
- Recommendations section
- Footer with zolletta-metaskill branding

---

## Phase 4 — Setup, review, and schema updates

### 4.1 Update `setup/assets/settings_template.json`

Add `"php": null` alongside the existing `"python": null`.

### 4.2 Update `setup/SKILL.md`

Add PHP tooling detection step (parallel to Step 6 for Python), run only when language is PHP:

- Read `composer.json` `require` and `require-dev`
- Read `autoload.psr-4` and `autoload-dev.psr-4`
- Detect tools: `phpunit`, `phpstan`, `psalm`, `php-cs-fixer`, `phpcs`
- Detect `php_version` from `composer.json` `require.php` constraint
- Detect `php-pro` skill availability (`~/.agents/skills/php-pro/SKILL.md`)
- Record `composer_mtime` for staleness check
- Populate `php` object in `settings.json` with `tools`, `code_style`, `testing`, `autoload`, `php_version`, `composer_mtime`

### 4.3 Update `review/SKILL.md`

Add PHP rows to the language-specific skills table:

| Language | Skill | Scope |
| --- | --- | --- |
| PHP | `php-code-style` | Types, modern PHP features, PSR-12, naming, security, performance |
| PHP | `php-testing-patterns` | PHPUnit naming, mirroring, coverage gaps, mocking, data providers |

### 4.4 Update root `SKILL.md`

- Add `php-code-style` and `php-testing-patterns` to the subcommand table
- Update "Supported languages" line from "Python / Others (Work in progress)" to "Python, PHP / Others (Work in progress)"

### 4.5 Update `docs/reference/settings-schema.md`

Add `php` section parallel to the existing `python` section, documenting:

- `php.tools` — phpunit, phpstan, psalm, php_cs_fixer, phpcs, php_pro_available
- `php.code_style` — all configurable rule toggles (keys from the 12 configurable rules)
- `php.testing` — check_test_naming, coverage thresholds
- `php.autoload` — psr-4, psr-4-dev
- `php.php_version` — detected from composer.json
- `php.composer_mtime` — for staleness check

### 4.6 Update `PLAN-PHP-SUPPORT.md`

Mark Phase 5.1 as superseded:

```markdown
### 5.1 Create `php-code-style/` skill

> **Superseded by PLAN-PHP-CODE-STYLE.md** — see that plan for the full 33-rule set (Type System, Modern PHP Features, PSR, Error Handling, Performance, Security), the report template, and version-gated configurable rules.
```

---

## Execution order

1. **Phase 0** — Frontmatter restructuring (frontmatter.md + 13 docs files)
2. **Phase 1.1** — Search skills.sh for Python equivalent of php-pro
3. **Phase 1.2** — Add php-pro "not installed" message to tool-messages.md
4. **Phase 2.1–2.3** — Create 3 general explanation docs (error-handling, performance, security)
5. **Phase 2.4** — Update docs/index.md with 3 new docs
6. **Phase 3.1** — Create php-code-style/SKILL.md (33 rules)
7. **Phase 3.2** — Create php-code-style/assets/report_template.md
8. **Phase 4.1** — Update settings_template.json (add php object)
9. **Phase 4.2** — Update setup/SKILL.md (PHP tooling detection + php-pro suggestion)
10. **Phase 4.3** — Update review/SKILL.md (PHP rows)
11. **Phase 4.4** — Update root SKILL.md (subcommand table + languages line)
12. **Phase 4.5** — Update settings-schema.md (php section)
13. **Phase 4.6** — Update PLAN-PHP-SUPPORT.md (mark Phase 5.1 superseded)

## Files to create

| File | Content |
| --- | --- |
| `docs/explanation/code/error-handling.md` | 4 general error handling rules (PHP + Python examples) |
| `docs/explanation/code/performance.md` | 2 general performance rules (PHP + Python examples) |
| `docs/explanation/code/security.md` | 4 general security rules (PHP + Python examples) |
| `php-code-style/SKILL.md` | 33 PHP-specific rules (21 always-on + 12 configurable) |
| `php-code-style/assets/report_template.md` | Report template matching patterns format |

## Files to modify

| File | Change |
| --- | --- |
| `docs/reference/frontmatter.md` | Document `python-*`, `php-*` wildcard syntax |
| `docs/index.md` | Add 3 new explanation docs + use `python-*` wildcard |
| `docs/reference/subcommands.md` | Use `python-*` wildcard |
| `docs/tutorials/getting-started.md` | Use `python-*` wildcard |
| `docs/reference/code/tokensave.md` | Use `python-*` wildcard |
| `docs/reference/code/review-mode.md` | Use `python-*` wildcard |
| `docs/explanation/code/structural-conventions.md` | Use `python-*` wildcard |
| `docs/explanation/code/python/python-review-patterns.md` | Use `python-*` wildcard |
| `docs/how-to/code/review-test-code.md` | Use `python-*` wildcard |
| `docs/how-to/code/review-code-style.md` | Use `python-*` wildcard |
| `docs/how-to/code/python/review-python-tests.md` | Use `python-*` wildcard |
| `docs/how-to/code/python/review-python-style.md` | Use `python-*` wildcard |
| `docs/reference/code/python/python-code-style.md` | Use `python-*` wildcard |
| `docs/reference/tool-messages.md` | Add php-pro "not installed" message |
| `setup/assets/settings_template.json` | Add `php` object |
| `setup/SKILL.md` | Add PHP tooling detection + php-pro suggestion |
| `review/SKILL.md` | Add PHP rows to language-specific table |
| `SKILL.md` | Add php-code-style to subcommand table + update languages line |
| `docs/reference/settings-schema.md` | Add `php` section |
| `PLAN-PHP-SUPPORT.md` | Mark Phase 5.1 as superseded |

## Verification

- [ ] `docs/reference/frontmatter.md` documents `python-*`, `php-*` wildcard syntax
- [ ] No docs file lists `python-code-style` or `python-testing-patterns` individually anymore
- [ ] `php-code-style/SKILL.md` has 33 rules (51 - 8 already covered - 10 promoted)
- [ ] No SOLID rules duplicated between `php-code-style` and `patterns/`
- [ ] No one-class-per-file rule duplicated between `php-code-style` and `shared/`
- [ ] Report template matches `patterns/assets/report_template.md` format
- [ ] General docs (`error-handling.md`, `performance.md`, `security.md`) have both PHP and Python examples
- [ ] `docs/index.md` lists the 3 new explanation docs in the Code review principles table
- [ ] `settings_template.json` has `php` object with `code_style` toggles
- [ ] `review/SKILL.md` has PHP rows in language-specific table
- [ ] `SKILL.md` has `php-code-style` in subcommand table
- [ ] `docs/reference/tool-messages.md` has php-pro "not installed" message
- [ ] `PLAN-PHP-SUPPORT.md` Phase 5.1 marked as superseded

## Risks / Considerations

- **php-pro is an implementation skill, not review** — zolletta-metaskill can only suggest installing it, not integrate it into the review workflow. The suggestion is informational only.
- **Version-gated rules** — PHP 8.0–8.5 features must be gated by detected `php_version`. Rules for newer versions are silently skipped (not flagged) when the project targets an older PHP version. The skill prints a summary of skipped rules.
- **Depends on PLAN-PHP-SUPPORT.md Phases 1–4** — `php-code-style/SKILL.md` can be written first (manual review guidance with grep-based detection), with automated tree-sitter scanners added later when `PhpEngine` is ready (Phase 2.3 of PLAN-PHP-SUPPORT.md).
- **10 promoted rules need Python examples** — the source material (php-best-practices) is PHP-only. Python examples must be written from scratch for `error-handling.md`, `performance.md`, and `security.md`.
- **Python equivalent of php-pro may not exist** — if the skills.sh search finds no suitable Python implementation skill, note it as a gap and move on. The php-pro suggestion remains PHP-only.
- **Frontmatter wildcard parsing** — any tooling that reads the `skills:` field (staleness scorer, drift detector) must be updated to expand `python-*` / `php-*` wildcards. Check `src/zolletta_metaskill/documentor/` for parsers that consume this field.
