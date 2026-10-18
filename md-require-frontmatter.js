// md-require-frontmatter.js — markdownlint custom rule.
//
// markdownlint has no built-in frontmatter rule, so the convention in
// docs/reference/frontmatter.md is enforced with this custom rule, loaded by
// .markdownlint-cli2.jsonc. It fires once per file that opens without a `---`
// block. Exemptions live in the cli2 `ignores` list (CHANGELOG.md), which is
// per-file and proven — per-path rule scoping is not.

"use strict";

module.exports = {
  names: ["require-frontmatter", "MD900"],
  description: "Documents must open with a YAML frontmatter block",
  tags: ["frontmatter"],
  function: function rule(params, onError) {
    if (!params.frontMatterLines || params.frontMatterLines.length === 0) {
      onError({
        lineNumber: 1,
        detail: "no YAML frontmatter (see docs/reference/frontmatter.md)",
      });
    }
  },
};
