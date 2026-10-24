---
status: triage
generated: 2026-10-24
source: mutmut run on branch 62-dogfooding
---

# Mutation testing triage

Run: 18784 mutants — 14466 killed, 4301 survived, 16 timeout, 1 suspicious.

This file groups the survivors so each module can be worked through as one task: look at the mutants with `uv run mutmut browse`, decide per mutant whether it is a test gap or an equivalent, then kill it with a test or silence it with `# pragma: no mutate`. A `touch` of the source file forces `mutmut run` to retest its mutants.

## Categories

| Bucket                   | Meaning                                                           | Action                                                                             |
| ------------------------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `behavioral`             | mutant changes a returned value, condition, loop or raise         | **write a test** asserting the real output                                         |
| `output-observable`      | mutant touches print/logging — stdout is the CLI contract (cli.3) | **write a test** on emitted text                                                   |
| `argparse-text`          | mutant on help/description/parser wiring                          | **done** — silenced per-line (`help=`/`description=`/`metavar=` lines only)        |
| `check-manually`         | small literal/`None`/flag flips; classifier unsure                | eyeball in `mutmut browse`; often equivalent                                       |
| `equivalent`             | auto-detected (e.g. `encoding="utf-8"` → `None`)                  | **done** — silenced with `# pragma: no mutate`                                     |
| `timeout` / `suspicious` | rerun anomalies                                                   | rerun or investigate                                                               |

## Modules by survivor count

| Module                                                                 | behavioral   | output   | argparse   | check   | equiv   | total   |
| ---------------------------------------------------------------------- | ------------ | -------- | ---------- | ------- | ------- | ------- |
| `zolletta_metaskill.documentor.quality.quality_scorer`                 | 126          | 0        | 0 | 120     | 0 | 249     |
| `zolletta_metaskill.documentor.api_doc.api_doc_validator`              | 109          | 0        | 0 | 103     | 0 | 217     |
| `zolletta_metaskill.documentor.quality.drift_detector`                 | 126          | 0        | 0 | 54      | 0 | 181     |
| `zolletta_metaskill.documentor.report_aggregator`                      | 122          | 0        | 0 | 27      | 0 | 152     |
| `zolletta_metaskill.testing_style.python.test_splitter`                | 51           | 60       | 0 | 6       | 0 | 151     |
| `zolletta_metaskill.code_style.python.docstring_streamliner`           | 107          | 0        | 0 | 28      | 0 | 148     |
| `zolletta_metaskill.core.engine.php_engine`                            | 134          | 0        | 0 | 13      | 0 | 147     |
| `zolletta_metaskill.documentor.links.link_checker`                     | 70           | 0        | 0 | 60      | 0 | 143     |
| `zolletta_metaskill.testing_style.general.test_structure_scanner`      | 39           | 26       | 0 | 52      | 0 | 123     |
| `zolletta_metaskill.documentor.quality.quality_report_writer`          | 77           | 0        | 0 | 30      | 0 | 107     |
| `zolletta_metaskill.documentor.quality.quality_review`                 | 95           | 5        | 0 | 0       | 0 | 105     |
| `zolletta_metaskill.patterns.general.liskov_substitution_scanner`      | 68           | 6        | 0 | 17      | 0 | 96      |
| `zolletta_metaskill.documentor.api_doc.api_doc_report_writer`          | 73           | 0        | 0 | 23      | 0 | 96      |
| `zolletta_metaskill.adr.adr_distiller`                                 | 84           | 0        | 0 | 8       | 0 | 95      |
| `zolletta_metaskill.code_style.php.acronym_casing_scanner`             | 60           | 14       | 0 | 10      | 0 | 90      |
| `zolletta_metaskill.code_style.python.unused_all_exports_scanner`      | 39           | 43       | 0 | 0       | 0 | 89      |
| `zolletta_metaskill.patterns.php.dependency_inversion_scanner`         | 54           | 23       | 0 | 6       | 0 | 88      |
| `zolletta_metaskill.documentor.quality.doc_accuracy_scorer`            | 63           | 0        | 0 | 22      | 0 | 87      |
| `zolletta_metaskill.patterns.python.open_closed_scanner`               | 50           | 26       | 0 | 0       | 0 | 82      |
| `zolletta_metaskill.code_style.general.cyclomatic_complexity_scanner`  | 54           | 6        | 0 | 16      | 0 | 81      |
| `zolletta_metaskill.code_style.general.one_class_per_file_scanner`     | 51           | 25       | 0 | 0       | 0 | 81      |
| `zolletta_metaskill.documentor.quality.unwrapped_prose_scanner`        | 68           | 6        | 0 | 0       | 0 | 80      |
| `zolletta_metaskill.testing_style.python.mutmut_survived_reporter`     | 68           | 5        | 0 | 2       | 0 | 80      |
| `zolletta_metaskill.code_style.general.naming_conventions_scanner`     | 33           | 23       | 0 | 14      | 0 | 76      |
| `zolletta_metaskill.code_style.python.acronym_casing_scanner`          | 53           | 5        | 0 | 10      | 0 | 75      |
| `zolletta_metaskill.documentor.api_doc.source_signature_extractor`     | 12           | 0        | 0 | 58      | 0 | 71      |
| `zolletta_metaskill.patterns.general.integration_graph_scanner`        | 59           | 1        | 0 | 3       | 0 | 68      |
| `zolletta_metaskill.patterns.php.open_closed_scanner`                  | 43           | 20       | 0 | 0       | 0 | 68      |
| `zolletta_metaskill.patterns.python.interface_segregation_scanner`     | 35           | 7        | 0 | 13      | 0 | 61      |
| `zolletta_metaskill.code_style.general.function_length_scanner`        | 36           | 6        | 0 | 14      | 0 | 61      |
| `zolletta_metaskill.patterns.php.interface_segregation_scanner`        | 35           | 19       | 0 | 0       | 0 | 59      |
| `zolletta_metaskill.code_style.general.max_arguments_scanner`          | 37           | 6        | 0 | 10      | 0 | 58      |
| `zolletta_metaskill.patterns.python.dependency_inversion_scanner`      | 38           | 6        | 0 | 6       | 0 | 56      |
| `zolletta_metaskill.documentor.quality.doc_completeness_scorer`        | 27           | 0        | 0 | 24      | 0 | 53      |
| `zolletta_metaskill.testing_style.python.test_naming_scanner`          | 43           | 2        | 0 | 3       | 0 | 53      |
| `zolletta_metaskill.documentor.api_doc.documented_item_extractor`      | 38           | 0        | 0 | 11      | 0 | 50      |
| `zolletta_metaskill.code_style.general.file_length_scanner`            | 25           | 17       | 0 | 0       | 0 | 47      |
| `zolletta_metaskill.patterns.general.class_metrics_scanner`            | 30           | 11       | 0 | 0       | 0 | 46      |
| `zolletta_metaskill.code_style.general.suppression_reason_scanner`     | 35           | 3        | 0 | 0       | 0 | 45      |
| `zolletta_metaskill.patterns.general.test_god_classes_scanner`         | 24           | 2        | 0 | 5       | 0 | 41      |
| `zolletta_metaskill.setup.python_paths_detector`                       | 31           | 3        | 0 | 0       | 0 | 40      |
| `zolletta_metaskill.documentor.documentor_client`                      | 34           | 0        | 0 | 0       | 0 | 39      |
| `zolletta_metaskill.documentor.utils.git_helper`                       | 23           | 0        | 0 | 16      | 0 | 39      |
| `zolletta_metaskill.documentor.links.external_url_checker`             | 39           | 0        | 0 | 0       | 0 | 39      |
| `zolletta_metaskill.adr.adr_orchestrator`                              | 21           | 0        | 0 | 13      | 0 | 35      |
| `zolletta_metaskill.documentor.utils.doc_code_mapper`                  | 24           | 0        | 0 | 7       | 0 | 33      |
| `zolletta_metaskill.documentor.links.link_report_writer`               | 32           | 0        | 0 | 1       | 0 | 33      |
| `zolletta_metaskill.setup.global_gitignore_ensurer`                    | 25           | 0        | 0 | 0       | 0 | 33      |
| `zolletta_metaskill.setup.adr_detector`                                | 24           | 0        | 0 | 0       | 0 | 30      |
| `zolletta_metaskill.adr.adr_client`                                    | 15           | 0        | 0 | 0       | 0 | 29      |
| `zolletta_metaskill.core.engine.python_engine`                         | 26           | 0        | 0 | 0       | 0 | 27      |
| `zolletta_metaskill.setup.php_tools_detector`                          | 13           | 3        | 0 | 0       | 0 | 22      |
| `zolletta_metaskill.setup.pyproject_sections_detector`                 | 12           | 3        | 0 | 0       | 0 | 21      |
| `zolletta_metaskill.core.project_config`                               | 18           | 0        | 0 | 0       | 0 | 19      |
| `zolletta_metaskill.documentor.utils.documentor_settings`              | 16           | 0        | 0 | 0       | 0 | 16      |
| `zolletta_metaskill.code_style.python.docstring_report_writer`         | 8            | 8        | 0 | 0       | 0 | 16      |
| `zolletta_metaskill.adr.adr_cache`                                     | 12           | 0        | 0 | 0       | 0 | 14      |
| `zolletta_metaskill.setup.doc_config_detector`                         | 8            | 0        | 0 | 0       | 0 | 13      |
| `zolletta_metaskill.setup.language_detector`                           | 8            | 0        | 0 | 0       | 0 | 13      |
| `zolletta_metaskill.adr.adr_discovery`                                 | 9            | 0        | 0 | 0       | 0 | 10      |
| `zolletta_metaskill.code_style.python.structs.docstring_strip_options` | 0            | 0        | 0 | 9       | 0 | 9       |
| `zolletta_metaskill.documentor.utils.fenced_content`                   | 7            | 0        | 0 | 0       | 0 | 8       |
| `zolletta_metaskill.setup.companion_skill_detector`                    | 0            | 3        | 0 | 0       | 0 | 7       |

## Work checklist

Order = highest payoff first (behavioral count). Tick the box when the module is done (tests added or mutants silenced).

- [ ] `zolletta_metaskill.documentor.quality.quality_scorer` — 126 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.api_doc.api_doc_validator` — 109 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.quality.drift_detector` — 126 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.report_aggregator` — 122 behavioral, 0 output
- [ ] `zolletta_metaskill.testing_style.python.test_splitter` — 51 behavioral, 60 output
- [ ] `zolletta_metaskill.code_style.python.docstring_streamliner` — 107 behavioral, 0 output
- [ ] `zolletta_metaskill.core.engine.php_engine` — 134 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.links.link_checker` — 70 behavioral, 0 output
- [ ] `zolletta_metaskill.testing_style.general.test_structure_scanner` — 39 behavioral, 26 output
- [ ] `zolletta_metaskill.documentor.quality.quality_report_writer` — 77 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.quality.quality_review` — 95 behavioral, 5 output
- [ ] `zolletta_metaskill.patterns.general.liskov_substitution_scanner` — 68 behavioral, 6 output
- [ ] `zolletta_metaskill.documentor.api_doc.api_doc_report_writer` — 73 behavioral, 0 output
- [ ] `zolletta_metaskill.adr.adr_distiller` — 84 behavioral, 0 output
- [ ] `zolletta_metaskill.code_style.php.acronym_casing_scanner` — 60 behavioral, 14 output
- [ ] `zolletta_metaskill.code_style.python.unused_all_exports_scanner` — 39 behavioral, 43 output
- [ ] `zolletta_metaskill.patterns.php.dependency_inversion_scanner` — 54 behavioral, 23 output
- [ ] `zolletta_metaskill.documentor.quality.doc_accuracy_scorer` — 63 behavioral, 0 output
- [ ] `zolletta_metaskill.patterns.python.open_closed_scanner` — 50 behavioral, 26 output
- [ ] `zolletta_metaskill.code_style.general.cyclomatic_complexity_scanner` — 54 behavioral, 6 output
- [ ] `zolletta_metaskill.code_style.general.one_class_per_file_scanner` — 51 behavioral, 25 output
- [ ] `zolletta_metaskill.documentor.quality.unwrapped_prose_scanner` — 68 behavioral, 6 output
- [ ] `zolletta_metaskill.testing_style.python.mutmut_survived_reporter` — 68 behavioral, 5 output
- [ ] `zolletta_metaskill.code_style.general.naming_conventions_scanner` — 33 behavioral, 23 output
- [ ] `zolletta_metaskill.code_style.python.acronym_casing_scanner` — 53 behavioral, 5 output
- [ ] `zolletta_metaskill.documentor.api_doc.source_signature_extractor` — 12 behavioral, 0 output
- [ ] `zolletta_metaskill.patterns.general.integration_graph_scanner` — 59 behavioral, 1 output
- [ ] `zolletta_metaskill.patterns.php.open_closed_scanner` — 43 behavioral, 20 output
- [ ] `zolletta_metaskill.patterns.python.interface_segregation_scanner` — 35 behavioral, 7 output
- [ ] `zolletta_metaskill.code_style.general.function_length_scanner` — 36 behavioral, 6 output
- [ ] `zolletta_metaskill.patterns.php.interface_segregation_scanner` — 35 behavioral, 19 output
- [ ] `zolletta_metaskill.code_style.general.max_arguments_scanner` — 37 behavioral, 6 output
- [ ] `zolletta_metaskill.patterns.python.dependency_inversion_scanner` — 38 behavioral, 6 output
- [ ] `zolletta_metaskill.documentor.quality.doc_completeness_scorer` — 27 behavioral, 0 output
- [ ] `zolletta_metaskill.testing_style.python.test_naming_scanner` — 43 behavioral, 2 output
- [ ] `zolletta_metaskill.documentor.api_doc.documented_item_extractor` — 38 behavioral, 0 output
- [ ] `zolletta_metaskill.code_style.general.file_length_scanner` — 25 behavioral, 17 output
- [ ] `zolletta_metaskill.patterns.general.class_metrics_scanner` — 30 behavioral, 11 output
- [ ] `zolletta_metaskill.code_style.general.suppression_reason_scanner` — 35 behavioral, 3 output
- [ ] `zolletta_metaskill.patterns.general.test_god_classes_scanner` — 24 behavioral, 2 output
- [ ] `zolletta_metaskill.setup.python_paths_detector` — 31 behavioral, 3 output
- [ ] `zolletta_metaskill.documentor.documentor_client` — 34 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.utils.git_helper` — 23 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.links.external_url_checker` — 39 behavioral, 0 output
- [ ] `zolletta_metaskill.adr.adr_orchestrator` — 21 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.utils.doc_code_mapper` — 24 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.links.link_report_writer` — 32 behavioral, 0 output
- [ ] `zolletta_metaskill.setup.global_gitignore_ensurer` — 25 behavioral, 0 output
- [ ] `zolletta_metaskill.setup.adr_detector` — 24 behavioral, 0 output
- [ ] `zolletta_metaskill.adr.adr_client` — 15 behavioral, 0 output
- [ ] `zolletta_metaskill.core.engine.python_engine` — 26 behavioral, 0 output
- [ ] `zolletta_metaskill.setup.php_tools_detector` — 13 behavioral, 3 output
- [ ] `zolletta_metaskill.setup.pyproject_sections_detector` — 12 behavioral, 3 output
- [ ] `zolletta_metaskill.core.project_config` — 18 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.utils.documentor_settings` — 16 behavioral, 0 output
- [ ] `zolletta_metaskill.code_style.python.docstring_report_writer` — 8 behavioral, 8 output
- [ ] `zolletta_metaskill.adr.adr_cache` — 12 behavioral, 0 output
- [ ] `zolletta_metaskill.setup.doc_config_detector` — 8 behavioral, 0 output
- [ ] `zolletta_metaskill.setup.language_detector` — 8 behavioral, 0 output
- [ ] `zolletta_metaskill.adr.adr_discovery` — 9 behavioral, 0 output
- [ ] `zolletta_metaskill.documentor.utils.fenced_content` — 7 behavioral, 0 output

## Progress

- [x] `argparse-text` bucket (244 mutants on `help=`/`description=`/`metavar=`) — help text is not a tested contract (cli.3 covers findings on stdout, not usage prose); silenced per-line so behavioural mutants in the same functions stay live.
- [x] `equivalent` bucket (54 mutants, all `encoding="utf-8" → None`) — verified non-observable on POSIX/UTF-8 locales, silenced with `# pragma: no mutate` on the affected `read_text`/`write_text` calls.

## Anomalies

- 1 suspicious, 16 timeouts — rerun with `uv run mutmut run` after the first batch of fixes; timeouts usually resolve once sibling mutants are killed.
