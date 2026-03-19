# Changelog — pep# VS Code Extension

## 0.1.0-beta (2026-03-13)

### Added
- Syntax highlighting for `.pep` and `.pepc` files
- TextMate grammar covering:
  - All keywords and control flow
  - Pipeline operator `->`, assignment `:=`, error operator `?`
  - Pipeline stages: `filter`, `map`, `collect`, etc.
  - Data sources: `json`, `csv`, `file`, `http`, `parquet`
  - Built-in types: `number`, `string`, `pipeline`, etc.
  - String interpolation `{var}` inside double-quoted strings
  - Comment highlighting with `#`
- Autocompletion:
  - Context-aware: after `->` shows pipeline stages; after `:=` shows sources; after `use` shows modules
  - Full keyword completions with snippet insertion
  - Hover documentation for all major keywords and operators
- 26 built-in snippets (fn, if, for, server, task, pipeline, etc.)
- Language configuration: bracket matching, auto-closing pairs, indentation rules
- `pep# Run File` command accessible from the editor title bar
- `pep# Watch Pipeline` command via Command Palette
- Status bar indicator for active `.pep` files
- Extension icon (pep# logo)
