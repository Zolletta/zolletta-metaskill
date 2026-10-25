---
status: triage
generated: 2026-10-25
source: mutmut run on branch 62-dogfooding (fresh, post-pragma fix)
---

# Mutation testing triage — per file

**Final reconciled run (mutants.4): 16817 mutants — 16798 killed (99.9%), 0 survived, 18 timeout, 1 suspicious (stale flag, verified killed manually).**

Survivors grouped **per source file → per method** (mutant numbers match `uv run mutmut browse`). Workflow: inspect the mutant, kill it with a test or silence it with a pragma, then retest with `uv run mutmut run <names>`.

Categories: `behavioral` = logic/output change · `output` = stdout text (cli.3 contract) · s`dictget-*` = `.get()` default/key mutants → test missing/present key · `assign/call/bool-none` = `→None`/`→True/False` flips → test produced value · `string-lit`/`numeric-lit`/`chk` = inspect before acting · `argparse-text`/`equivalent` = leftovers the regions missed → extend the pragma region.

Closed so far (66 files, 0 survivors each): `naming_conventions_scanner`, `fenced_content`, `adr_cache`, `adr_discovery`, `companion_skill_detector`, `doc_config_detector`, `language_detector`, `docstring_strip_options`, `api_doc_validator`, `quality_scorer`, `interface_segregation_scanner` (php + py), `file_length_scanner`, `class_metrics_scanner`, `doc_completeness_scorer`, `documented_item_extractor`, `test_naming_scanner`, `adr_detector`, `php_tools_detector`, `pyproject_sections_detector`, `global_gitignore_ensurer`, `project_config`, `adr_client`, `docstring_report_writer`, `documentor_settings`, `doc_code_mapper`, `python_engine`, `adr_orchestrator`, `link_report_writer`, `documentor_client`, `python_paths_detector`, `test_god_classes_scanner`, `suppression_reason_scanner`, `external_url_checker`, `git_helper`, `drift_detector`, `quality_review`, `integration_graph_scanner`, `report_aggregator`, `docstring_streamliner`, `test_structure_scanner`, `link_checker`, `liskov_substitution_scanner`, `unwrapped_prose_scanner`, `doc_accuracy_scorer`, `acronym_casing_scanner` (py + php), `adr_distiller`, `function_length_scanner`, `source_signature_extractor`, `mutmut_survived_reporter`, `api_doc_report_writer`, `quality_report_writer`, `dependency_inversion_scanner` (py + php), `open_closed_scanner` (py + php), `unused_all_exports_scanner`, `one_class_per_file_scanner`, `cyclomatic_complexity_scanner`, `test_splitter`, `max_arguments_scanner`, `grice_scanner`, `manner_metrics`, `quality_metrics`, `quantity_metrics`, `relation_metrics`, `similarity`, `markdown_corpus`, `corpus_normalizer`. Suspicious `link_checker.validate_link` verified killed manually (flag is stale stats).

Timeouts (18) are `i += 1` → `i = 1` / `while` guard flips → infinite loops, **already detected by timeout** — no action needed, listed at the bottom.

## Files

