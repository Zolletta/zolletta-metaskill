# Expected findings

Manifest mapping each playground file to the scanners that should report it. Verified empirically — if a scanner is run from `playground/` and reports something not listed here (or misses something listed), update this table.

| File | Scanner | Expected finding |
|---|---|---|
| `src/playground/user_manager.py` | `code_style/general/one_class_per_file_scanner.py` | 2 classes (`ApiHandler`, `UnusedHelper`) |
| `src/playground/user_manager.py` | `code_style/general/cyclomatic_complexity_scanner.py` | `reconcile_accounts` complexity 16 (> 12) |
| `src/playground/user_manager.py` | `code_style/general/max_arguments_scanner.py` | `create_user` (7), `build_report` (8) |
| `src/playground/user_manager.py` | `code_style/general/suppression_reason_scanner.py` | two `# type: ignore` without code/reason |
| `src/playground/user_manager.py` | `code_style/python/acronym_casing_scanner.py` | `ApiHandler` — `Api` should be `API` |
| `src/playground/user_manager.py` | `code_style/python/unused_all_exports_scanner.py` | all 3 `__all__` entries unused |
| `src/playground/user_manager.py` | `testing_style/general/test_structure_scanner.py` | missing test (`test_user_manager*.py`) |
| `src/playground/user_manager.py` | `patterns/general/class_metrics_scanner.py` | `ApiHandler` listed (top-N report) |
| `src/playground/user_manager.py` | `patterns/general/integration_graph_scanner.py` | edge to `string_utils.py` |
| `src/playground/string_utils.py` | `code_style/general/one_class_per_file_scanner.py` | zero-class file (low severity) |
| `src/playground/string_utils.py` | `testing_style/general/test_structure_scanner.py` | `test_string_utils.py` reported orphaned (no class to mirror) |
| `src/playground/report_engine.py` | `code_style/general/one_class_per_file_scanner.py` | 5 classes |
| `src/playground/report_engine.py` | `patterns/python/open_closed_scanner.py` | isinstance if/elif type ladder (4 branches + nested tail) |
| `src/playground/report_engine.py` | `testing_style/general/test_structure_scanner.py` | missing test (`test_report_engine*.py`) |
| `src/playground/notification_service.py` | `code_style/general/one_class_per_file_scanner.py` | 2 classes |
| `src/playground/notification_service.py` | `code_style/python/acronym_casing_scanner.py` | — (SmtpMailer removed; see `user_manager.py`) |
| `src/playground/notification_service.py` | `patterns/python/interface_segregation_scanner.py` | fat ABC `BroadChannel` (6 methods) + 4 stub methods |
| `src/playground/notification_service.py` | `testing_style/general/test_structure_scanner.py` | missing test (`test_notification_service*.py`) |
| `src/playground/checkout_service.py` | `code_style/general/one_class_per_file_scanner.py` | 3 classes |
| `src/playground/checkout_service.py` | `patterns/python/dependency_inversion_scanner.py` | `CheckoutService.__init__` news `StripeGateway`, `MysqlOrderRepository` |
| `src/playground/checkout_service.py` | `testing_style/general/test_structure_scanner.py` | missing test (`test_checkout_service*.py`) |
| `tests/test_stuff.py` | `code_style/general/one_class_per_file_scanner.py` | 2 `Test*` classes |
| `tests/test_stuff.py` | `code_style/general/naming_conventions_scanner.py` | no source matching `stuff` |
| `tests/test_stuff.py` | `testing_style/python/test_naming_scanner.py` | `test_x`, `test_y` (< 3 segments); `testItWorks`, `test2` unscanned |
| `tests/test_stuff.py` | `patterns/general/test_god_classes_scanner.py` | classes listed (top-N report) |
| `tests/test_stuff.py` | `testing_style/general/test_structure_scanner.py` | orphaned test |
| `tests/helper.py` | — | tests.4 is unenforced by design; illustration only |
| `src-php/ApiClient.php` | `code_style/php/acronym_casing_scanner.py` | `ApiClient` — `Api` should be `API` |
| `src-php/ApiClient.php` | `code_style/general/max_arguments_scanner.py` | `fetchDataFromRemoteEndpoint` (6 params) |
| `src-php/OrderProcessor.php` | `code_style/general/one_class_per_file_scanner.py` | 6 classes |
| `src-php/OrderProcessor.php` | `patterns/php/open_closed_scanner.py` | instanceof if/elseif ladder (4 branches) |
| `src-php/OrderProcessor.php` | `patterns/php/interface_segregation_scanner.py` | fat interface `Worker` (6 methods) |
| `src-php/CheckoutService.php` | `code_style/general/one_class_per_file_scanner.py` | 3 classes |
| `src-php/CheckoutService.php` | `patterns/php/dependency_inversion_scanner.py` | `__construct` news `StripeGateway`, `MysqlOrderRepository` |
| `tests-php/WhateverTest.php` | — | php test-naming scanner does not exist; illustration only |
| `docs/index.md` | `documentor/quality/unwrapped_prose_scanner.py` | wrapped paragraph at line 3 |
| `docs/index.md` | `documentor/links/link_checker.py` | broken link `missing/page.md`; absolute GitHub URL counted external |
| `docs/explanation/adr/ADR-001.md` | — | documentation.5 unenforced; invisible to ADR tooling by design |

## Deliberately clean

| File | Why |
|---|---|
| `tests/test_string_utils.py` | mirror test present so the suite is not degenerate — but still reported *orphaned* because `string_utils.py` defines no class |
| `src/playground/__init__.py` | makes `src/playground` a package so mirror scanners can auto-detect `python.paths.package` |

## Findings the playground cannot produce

- `functions.4` (unannotated signatures) — gated by `mypy`/`ty`, which exclude `playground/`.
- File-length (`classes.6`, `max_file_length`) — capped at 800 lines; no file approaches it.
- Missing trailing newline — would break the repo's own `general.1` gate.
- PHP test naming / test structure — no PHP-aware testing scanners exist yet.
