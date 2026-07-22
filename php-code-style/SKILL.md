---
name: php-code-style
version: 2.0.0
license: MIT + Commons Clause
description: >
  PHP code style review: strict typing, modern PHP 8.x features, PSR-12 compliance,
  naming conventions, error handling, performance, and security. Version-gated by
  detected php_version. Use when reviewing PHP code for style, type safety, or
  modern PHP feature adoption.
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
  - write
  - mcp_call_tool
  - mcp_list_tools
  - skill
permissions:
  allow:
    - Write(.zolletta-metaskill/**)
---

# PHP Code Style

Review PHP code for type safety, modern PHP feature adoption, PSR-12 compliance, naming conventions, error handling, performance, and security. Rules are version-gated by the detected `php_version` from `settings.json`.

> **Configuration source**: all project-level configuration (tool availability, rule toggles, PHP version) is read from `settings.json` — specifically the `php.tools.*` objects (availability + effective config), `php.code_style` (rule toggles), and `php.php_version`. These are populated by `setup` from `composer.json` and declarative config files. Do not read `composer.json` directly; do not hardcode fallback defaults. See the parent `SKILL.md` for the setup guard and the shared "Running tools" convention.

> **Review mode**: when this skill is invoked as part of a read-only review (e.g. `/zolletta-metaskill review`), follow the rules in [`../docs/reference/code/review-mode.md`](../docs/reference/code/review-mode.md) — do not apply fixes, classify diagnostics into auto-fixable (informational) vs. not auto-fixable (findings).

## When to Use This Skill

- Reviewing PHP code for type safety and strict typing
- Checking adoption of modern PHP 8.x features
- Enforcing PSR-12 coding style compliance
- Reviewing PHP naming conventions and namespace usage
- Configuring PHPStan, Psalm, php-cs-fixer, or phpcs

## Table 1 — Always-on rules (cannot be disabled)

| #   | Area     | Name                                                       | Min PHP |
| --- | -------- | ---------------------------------------------------------- | ------- |
| 1   | Types    | `declare(strict_types=1)` in every file                    | 7.0+    |
| 2   | Types    | Return type declarations on all methods                    | 7.0+    |
| 3   | Types    | Parameter type declarations                                | 7.0+    |
| 4   | Types    | Property type declarations                                 | 7.4+    |
| 5   | Types    | Nullable types explicitly declared (`?Type`)               | 7.1+    |
| 6   | Types    | Use `void`/`never` for appropriate returns                 | 8.1+    |
| 7   | Types    | Avoid `mixed` when a specific type is possible             | 8.0+    |
| 8   | Modern   | Constructor property promotion                             | 8.0+    |
| 9   | Modern   | Match expression over switch                               | 8.0+    |
| 10  | Modern   | Nullsafe operator (`?->`) for null chains                  | 8.0+    |
| 11  | Modern   | Named arguments for clarity                                | 8.0+    |
| 12  | Modern   | Attributes (`#[Attribute]`) for metadata (not docblocks)   | 8.0+    |
| 13  | Modern   | Enums instead of class constants for finite sets           | 8.1+    |
| 14  | Modern   | Readonly properties for immutable data                     | 8.1+    |
| 15  | Modern   | Arrow functions for short closures                         | 7.4+    |
| 16  | PSR      | PSR-4 autoloading compliance                               | all     |
| 17  | PSR      | PSR-12 coding style compliance                             | all     |
| 18  | PSR      | camelCase method names                                     | all     |
| 19  | PSR      | Proper namespace usage (matches directory structure)       | all     |
| 20  | Error    | Never use `@` error suppression operator                   | all     |
| 21  | Security | Validate file uploads (type, size, name, storage location) | all     |

## Table 2 — Configurable rules (stored in `settings.json` under `php.code_style`)

| #   | Area   | Name                              | Key                              | Default | Min PHP |
| --- | ------ | --------------------------------- | -------------------------------- | ------- | ------- |
| 22  | Types  | Union types                       | `check_union_types`              | `true`  | 8.0+    |
| 23  | Types  | Intersection types                | `check_intersection_types`       | `true`  | 8.1+    |
| 24  | Modern | Enums with methods                | `check_enum_methods`             | `true`  | 8.1+    |
| 25  | Modern | First-class callable syntax       | `check_first_class_callables`    | `true`  | 8.1+    |
| 26  | Modern | Readonly classes                  | `check_readonly_classes`         | `true`  | 8.2+    |
| 27  | Modern | Typed class constants             | `check_typed_constants`          | `true`  | 8.3+    |
| 28  | Modern | `#[\Override]` attribute          | `check_override_attribute`       | `true`  | 8.3+    |
| 29  | Modern | Property hooks                    | `check_property_hooks`           | `true`  | 8.4+    |
| 30  | Modern | Asymmetric visibility             | `check_asymmetric_visibility`    | `true`  | 8.4+    |
| 31  | Modern | Pipe operator                     | `check_pipe_operator`            | `true`  | 8.5+    |
| 32  | Perf   | Native array functions over loops | `check_array_functions`          | `true`  | all     |
| 33  | Perf   | Native string functions over regex| `check_string_functions`         | `true`  | all     |

## Version gating

Rules whose minimum PHP version is higher than the detected `php_version` are silently skipped (not flagged). The skill prints a note at the start of the review:

```text
ℹ Rules #6, #13–14, #22–31 skipped (require PHP 8.1+–8.5+, project targets 8.0).
```

If `php_version` is not set in `settings.json`, all rules are evaluated (assume the latest PHP version).

## Procedure

### Step 1 — Read configuration

Read `settings.json`:
- `php.php_version` — target PHP version (e.g. `"8.2"`)
- `php.code_style` — configurable rule toggles (Table 2)
- `php.tools.*` — tool availability (phpstan, psalm, php_cs_fixer, phpcs)

### Step 2 — Run external tools

For each available tool, run it and collect output:

| Tool           | Command (inside container if `container_name` is set)                    |
| -------------- | ------------------------------------------------------------------------ |
| PHPStan        | `phpstan analyse --no-progress --error-format=raw`                       |
| Psalm          | `psalm --no-progress --output-format=text`                               |
| php-cs-fixer   | `php-cs-fixer fix --dry-run --diff`                                      |
| phpcs          | `phpcs --report=emacs`                                                   |

Classify tool output:
- **Auto-fixable** (formatting, import order, style) → informational, not graded
- **Not auto-fixable** (type errors, missing declarations, logic issues) → findings with severity

### Step 3 — Apply always-on rules (Table 1)

For each `.php` file in the scanned directory, check the 21 always-on rules. Skip rules whose min PHP version exceeds the detected `php_version`.

### Step 4 — Apply configurable rules (Table 2)

For each configurable rule that is `true` in `php.code_style`, check it. Skip rules whose min PHP version exceeds the detected `php_version`.

### Step 5 — Write report

Write the report to `.zolletta-metaskill/reports/<timestamp>/php-code-style.md` using the [report template](assets/report_template.md).

## Rule details

### Type System rules (#1–#7, #22–#23)

- **#1 `declare(strict_types=1)`** — every `.php` file must start with `declare(strict_types=1);` as the first statement (after the opening `<?php` tag). This prevents implicit type coercion bugs.
- **#2 Return types** — every method must declare a return type. Exceptions: constructors (`__construct`), destructors (`__destruct`), and `__clone` which implicitly return `void`.
- **#3 Parameter types** — every parameter must have a type declaration. Use `mixed` only when genuinely unknown (but see rule #7).
- **#4 Property types** — every class property must have a type declaration (PHP 7.4+ typed properties).
- **#5 Nullable types** — use `?Type` explicitly instead of `Type|null` in unions for single nullable types.
- **#6 `void`/`never`** — use `void` for methods that return nothing, `never` for methods that never return (throw or exit). PHP 8.1+ for `never`.
- **#7 Avoid `mixed`** — when a specific type or union is possible, use it instead of `mixed`. `mixed` is acceptable only for genuinely dynamic values (e.g. decoded JSON).
- **#22 Union types** — prefer union types (`A|B`) over `mixed` when the value can be one of several known types. PHP 8.0+.
- **#23 Intersection types** — use intersection types (`A&B`) when a value must implement multiple interfaces. PHP 8.1+.

### Modern PHP Features (#8–#15, #24–#31)

- **#8 Constructor promotion** — use constructor property promotion (`public function __construct(private readonly int $id)`) instead of manual assignment. PHP 8.0+.
- **#9 Match expression** — use `match` instead of `switch` for value matching (returns a value, is strict, exhausts cases). PHP 8.0+.
- **#10 Nullsafe operator** — use `?->` for null-safe method chaining instead of manual null checks. PHP 8.0+.
- **#11 Named arguments** — use named arguments for functions with many optional parameters (`foo(limit: 10, offset: 0)`). PHP 8.0+.
- **#12 Attributes** — use `#[Attribute]` syntax instead of docblock annotations for metadata. PHP 8.0+.
- **#13 Enums** — use `enum` instead of class constants for finite sets (status codes, types). PHP 8.1+.
- **#14 Readonly properties** — use `readonly` for immutable data properties. PHP 8.1+.
- **#15 Arrow functions** — use `fn() =>` for short one-expression closures. PHP 7.4+.
- **#24 Enum methods** — enums should have methods instead of external switch/match on cases. PHP 8.1+.
- **#25 First-class callables** — use `$obj->method(...)` syntax instead of `Closure::fromCallable()`. PHP 8.1+.
- **#26 Readonly classes** — use `readonly class` for immutable value objects. PHP 8.2+.
- **#27 Typed constants** — use typed class constants (`const string FOO = 'bar'`). PHP 8.3+.
- **#28 `#[\Override]`** — mark methods that override parent methods with `#[\Override]` attribute. PHP 8.3+.
- **#29 Property hooks** — use property hooks for computed/validated properties instead of getters/setters. PHP 8.4+.
- **#30 Asymmetric visibility** — use `public private(set)` for read-public/write-private properties. PHP 8.4+.
- **#31 Pipe operator** — use `|>` operator for chaining transformations. PHP 8.5+.

### PSR Standards (#16–#19)

- **#16 PSR-4** — class names, namespaces, and file paths must follow PSR-4 autoloading. `App\Domain\User` lives in `src/Domain/User.php`.
- **#17 PSR-12** — coding style compliance (opening tag, brace placement, line length, indentation). Use php-cs-fixer or phpcs to verify.
- **#18 camelCase methods** — method names use camelCase: `getUserById()`, not `get_user_by_id()` or `GetUserById()`.
- **#19 Namespace usage** — namespaces must match directory structure. `App\Services\PaymentService` lives in `src/Services/PaymentService.php`.

### Error Handling (#20)

- **#20 No `@` suppression** — never use the `@` error suppression operator. It hides errors, makes debugging impossible, and has performance overhead. Handle errors explicitly with try/catch or error handling functions.

### Performance (#32–#33)

- **#32 Array functions** — use native array functions (`array_map`, `array_filter`, `array_column`, `array_reduce`) instead of manual `foreach` loops when transforming or filtering arrays.
- **#33 String functions** — use native string functions (`str_contains`, `str_starts_with`, `str_ends_with`, `strpos`) instead of regex (`preg_match`) when the pattern is a literal.

### Security (#21)

- **#21 File uploads** — validate `$_FILES` entries: check `UPLOAD_ERR_OK`, verify MIME type with `finfo_file()`, enforce size limits, generate safe filenames (never trust client-provided names), store outside the web root.

## Shared resources

- [`../docs/reference/code/review-mode.md`](../docs/reference/code/review-mode.md) — read-only review conventions
- [`../docs/explanation/code/error-handling.md`](../docs/explanation/code/error-handling.md) — language-agnostic error handling rules
- [`../docs/explanation/code/performance.md`](../docs/explanation/code/performance.md) — language-agnostic performance rules
- [`../docs/explanation/code/security.md`](../docs/explanation/code/security.md) — language-agnostic security rules
- [`../docs/reference/code/php/php-review-patterns.md`](../docs/explanation/code/php/php-review-patterns.md) — PHP-specific review patterns
