'use strict';

// ─── pep# VS Code Extension ───────────────────────────────────────────────────
// Provides: syntax coloring (via grammar), autocomplete, snippets,
// hover docs, and run/watch commands.
// No npm dependencies – uses only the vscode built-in API.

const vscode = require('vscode');
const cp     = require('child_process');
const path   = require('path');
const os     = require('os');

// ─────────────────────────────────────────────────────────────────────────────
// Completion data
// ─────────────────────────────────────────────────────────────────────────────

const CIK = vscode.CompletionItemKind;

const KEYWORDS = [
  // ── Control flow ──────────────────────────────────────────────────────────
  { label: 'if',     kind: CIK.Keyword, snippet: 'if ${1:condition}:\n    ${0}',         detail: 'if condition:', doc: 'Conditional statement.' },
  { label: 'elif',   kind: CIK.Keyword, snippet: 'elif ${1:condition}:',                 detail: 'elif condition:' },
  { label: 'else',   kind: CIK.Keyword, snippet: 'else:\n    ${0}',                       detail: 'else:' },
  { label: 'for',    kind: CIK.Keyword, snippet: 'for ${1:item} in ${2:list}:\n    ${0}', detail: 'for x in list:', doc: 'Iterate over a collection.' },
  { label: 'repeat', kind: CIK.Keyword, snippet: 'repeat ${1:10}:\n    ${0}',             detail: 'repeat N:',    doc: 'Repeat a block N times.' },
  { label: 'while',  kind: CIK.Keyword, snippet: 'while ${1:condition}:\n    ${0}',       detail: 'while cond:' },
  { label: 'return', kind: CIK.Keyword, snippet: 'return ${0}',                           detail: 'return value' },
  { label: 'match',  kind: CIK.Keyword, snippet: 'match ${1:expr}:\n    ${2:val} => ${0}', detail: 'match expr:', doc: 'Pattern matching.' },

  // ── Declarations ──────────────────────────────────────────────────────────
  { label: 'fn',   kind: CIK.Keyword, snippet: 'fn ${1:name}(${2:params}):\n    ${0}', detail: 'fn name(params):', doc: 'Declare a function.' },
  { label: 'use',  kind: CIK.Keyword, snippet: 'use ${0:module}',                      detail: 'use module',       doc: 'Import a module.' },
  { label: 'type', kind: CIK.Keyword, snippet: 'type ${1:Name}:\n    ${2:field}: ${3:string}\n    ${0}', detail: 'type Name:', doc: 'Declare a type schema.' },
  { label: 'mut',  kind: CIK.Keyword, snippet: 'mut ${1:name} := ${0}',               detail: 'mut name := …' },
  { label: 'set',  kind: CIK.Keyword, snippet: 'set ${1:name} = ${0}',                detail: 'set name = …',    doc: 'Update a mutable variable.' },

  // ── Concurrency ───────────────────────────────────────────────────────────
  { label: 'task',  kind: CIK.Keyword, snippet: 'task ${1:name}:\n    ${0}', detail: 'task name:', doc: 'Async task declaration.' },
  { label: 'await', kind: CIK.Keyword, snippet: 'await ${1:task1}',          detail: 'await task1, task2', doc: 'Wait for one or more named tasks.' },
  { label: 'taskgroup', kind: CIK.Keyword, snippet: 'taskgroup ${1:name}:\n    task ${2:step1}:\n        ${0}', detail: 'taskgroup name:' },

  // ── Server ────────────────────────────────────────────────────────────────
  { label: 'server', kind: CIK.Keyword, snippet: 'server ${1:8080}:\n    route "${2:/}":\n        return ${0}', detail: 'server port:', doc: 'Embedded HTTP server.' },
  { label: 'route',  kind: CIK.Keyword, snippet: 'route "${1:/path}":\n    return ${0}',                        detail: 'route "/path":', doc: 'HTTP route inside a server.' },

  // ── Observability ─────────────────────────────────────────────────────────
  { label: 'watch',   kind: CIK.Keyword, snippet: 'watch ${0:pipeline}', detail: 'watch pipeline', doc: 'Print pipeline execution metrics.' },
  { label: 'trace',   kind: CIK.Keyword, snippet: 'trace ${0:pipeline}', detail: 'trace pipeline' },
  { label: 'explain', kind: CIK.Keyword, snippet: 'explain ${0:pipeline}',detail: 'explain pipeline' },

  // ── Error handling ────────────────────────────────────────────────────────
  { label: 'permit', kind: CIK.Keyword, snippet: 'permit ${1:fs.read} "${0:data/}"', detail: 'permit capability "path"' },
];

const PIPELINE_STAGES = [
  { label: 'filter',           snippet: 'filter ${1:condition}',          doc: 'Keep items that match a condition.' },
  { label: 'map',              snippet: 'map ${1:expr}',                  doc: 'Transform each item.' },
  { label: 'flatmap',          snippet: 'flatmap ${1:expr}',              doc: 'Map and flatten one level.' },
  { label: 'reduce',           snippet: 'reduce ${1:expr}',               doc: 'Reduce all items to a single value.' },
  { label: 'collect',          snippet: 'collect',                        doc: 'Materialize the stream into a list.' },
  { label: 'count',            snippet: 'count',                          doc: 'Count items in the stream.' },
  { label: 'take',             snippet: 'take ${1:10}',                   doc: 'Take the first N items.' },
  { label: 'drop',             snippet: 'drop ${1:10}',                   doc: 'Drop the first N items.' },
  { label: 'skip',             snippet: 'skip ${1:10}',                   doc: 'Skip the first N items (alias for drop).' },
  { label: 'save',             snippet: 'save "${1:output.json}"',        doc: 'Save stream to a file.' },
  { label: 'store',            snippet: 'store "${1:output.json}"',       doc: 'Store stream (alias for save).' },
  { label: 'print',            snippet: 'print',                          doc: 'Print each item to stdout.' },
  { label: 'parse json',       snippet: 'parse json',                     doc: 'Parse a JSON string to a value.' },
  { label: 'group by',         snippet: 'group by ${1:key}',              doc: 'Group items by a key expression.' },
  { label: 'sort by',          snippet: 'sort by ${1:key}',               doc: 'Sort items by a key expression.' },
  { label: 'join',             snippet: 'join ${1:other} on ${2:key}',    doc: 'Join with another pipeline on a key.' },
  { label: 'merge',            snippet: 'merge ${1:other}',               doc: 'Merge two pipelines.' },
  { label: 'parallel max',     snippet: 'parallel max ${1:4}',            doc: 'Set the parallelism level for this stage.' },
  { label: 'batch',            snippet: 'batch ${1:100}',                 doc: 'Process items in batches of N.' },
  { label: 'buffer',           snippet: 'buffer ${1:1000}',               doc: 'Buffer up to N items before backpressure.' },
  { label: 'step',             snippet: 'step ${1:name}:\n    ${0}',      doc: 'Named sub-step for observability.' },
  { label: 'validate schema',  snippet: 'validate schema ${1:Type}',      doc: 'Validate items against a type schema.' },
  { label: 'window tumbling',  snippet: 'window tumbling ${1:30s}',       doc: 'Tumbling time window.' },
  { label: 'window sliding',   snippet: 'window sliding ${1:60s} every ${2:30s}', doc: 'Sliding time window.' },
  { label: 'distinct',         snippet: 'distinct',                       doc: 'Remove duplicate items.' },
  { label: 'sample',           snippet: 'sample ${1:100}',               doc: 'Sample up to N random items.' },
];

const SOURCE_KEYWORDS = [
  { label: 'json',     snippet: 'json "${1:data.json}"',               doc: 'Read a JSON file as pipeline source.' },
  { label: 'csv',      snippet: 'csv "${1:data.csv}"',                 doc: 'Read a CSV file (each row as a map).' },
  { label: 'file',     snippet: 'file "${1:data.txt}"',                doc: 'Read raw file content as a string.' },
  { label: 'files',    snippet: 'files "${1:data/}"',                  doc: 'Read all files from a directory.' },
  { label: 'http get', snippet: 'http get "${1:https://api.example}"', doc: 'HTTP GET request.' },
  { label: 'parquet',  snippet: 'parquet "${1:data.parquet}"',         doc: 'Read a Parquet file.' },
  { label: 'stream',   snippet: 'stream ${1:kafka} "${2:topic}"',      doc: 'Event stream source.' },
];

const MODULES = [
  { label: 'use http',    snippet: 'use http',     doc: 'HTTP client module.' },
  { label: 'use json',    snippet: 'use json',     doc: 'JSON utilities.' },
  { label: 'use csv',     snippet: 'use csv',      doc: 'CSV utilities.' },
  { label: 'use crypto',  snippet: 'use crypto',   doc: 'Cryptography primitives.' },
  { label: 'use time',    snippet: 'use time',     doc: 'Date and time utilities.' },
  { label: 'use math',    snippet: 'use math',     doc: 'Math functions.' },
  { label: 'use fs',      snippet: 'use fs',       doc: 'Filesystem utilities.' },
  { label: 'use parquet', snippet: 'use parquet',  doc: 'Apache Parquet I/O.' },
  { label: 'use test',    snippet: 'use test',     doc: 'Test assertion utilities.' },
  { label: 'use observe', snippet: 'use observe',  doc: 'Observability and metrics.' },
  { label: 'use cloud',   snippet: 'use cloud',    doc: 'Cloud storage integrations.' },
];

const TYPES = [
  'number', 'string', 'boolean', 'list', 'map',
  'pipeline', 'error', 'result', 'option',
  'time', 'duration', 'bytes', 'any', 'record',
];

// ─── Hover documentation ──────────────────────────────────────────────────────

const HOVER_DOCS = {
  '->': [
    '**`->`** — Pipeline operator',
    '',
    'Passes the output of the left expression to the next stage.',
    '',
    '```pep',
    'users -> filter age >= 18 -> map name -> collect',
    '```',
  ].join('\n'),

  ':=': [
    '**`:=`** — Binding operator',
    '',
    'Creates an immutable variable binding.',
    '',
    '```pep',
    'name := "Lucas"',
    'users := json "users.json"',
    '```',
  ].join('\n'),

  'fn': [
    '**`fn`** — Function declaration',
    '',
    '```pep',
    'fn soma(a, b):',
    '    return a + b',
    '',
    'fn double(x) => x * 2',
    '```',
  ].join('\n'),

  'task': [
    '**`task`** — Async task',
    '',
    'Tasks run concurrently. Use `await` to synchronize.',
    '',
    '```pep',
    'task ingest:',
    '    process data',
    '',
    'await ingest',
    '```',
  ].join('\n'),

  'await': [
    '**`await`** — Wait for tasks',
    '',
    '```pep',
    'await ingest, transform, publish',
    '```',
  ].join('\n'),

  'server': [
    '**`server`** — Embedded HTTP server',
    '',
    '```pep',
    'server 8080:',
    '    route "/":',
    '        return "Hello"',
    '',
    '    route "/users":',
    '        return users -> collect',
    '```',
  ].join('\n'),

  'watch': [
    '**`watch`** — Pipeline metrics',
    '',
    'Prints real-time metrics for each pipeline stage.',
    '',
    '```pep',
    'watch sales',
    '```',
    '',
    '```',
    'source            ok   3000 items    0.12 ms',
    'filter amount>=20 ok   2100 items    1.40 ms',
    'map amount        ok   2100 items    0.80 ms',
    'collect           ok   2100 items    0.10 ms',
    '```',
  ].join('\n'),

  'filter': [
    '**`filter`** — Pipeline stage',
    '',
    'Keep only items that match the condition.',
    '',
    '```pep',
    'users -> filter age >= 18',
    'orders -> filter status == "paid" and amount > 0',
    '```',
  ].join('\n'),

  'map': [
    '**`map`** — Pipeline stage',
    '',
    'Transform each item in the stream.',
    '',
    '```pep',
    'users -> map name',
    'items -> map { id: id, total: price * qty }',
    '```',
  ].join('\n'),

  'collect': '**`collect`** — Materialize the pipeline into a `list`.',
  'count':   '**`count`** — Count items and return a `number`.',
  'take':    '**`take N`** — Return the first N items.',
  'drop':    '**`drop N`** — Drop the first N items.',
  'reduce':  '**`reduce`** — Reduce all items to a single aggregated value.',
  'parallel': '**`parallel max N`** — Allow up to N workers to process this pipeline concurrently.',
  'save':    '**`save "path"`** — Write pipeline output to a file (JSON/CSV/Parquet).',
  'print':   '**`print`** — Print each item in the stream to stdout.',

  'if':     '**`if`** — Conditional. Body must be indented 4 spaces.',
  'for':    '**`for x in list:`** — Iterate over a collection.',
  'repeat': '**`repeat N:`** — Execute the body N times.',
  'return': '**`return`** — Return a value from a function or route.',
  'match':  '**`match expr:`** — Pattern match over a value.',
  'use':    '**`use module`** — Import a built-in or third-party module.',
  'type':   '**`type Name:`** — Declare a typed schema for pipeline validation.',
  'mut':    '**`mut name :=`** — Declare a mutable variable.',
  'permit': '**`permit capability "resource"`** — Declare an explicit sandbox permission.',
};

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function makeItem(label, kind, doc, snippet, detail) {
  const item = new vscode.CompletionItem(label, kind);
  if (doc)     item.documentation = new vscode.MarkdownString(doc);
  if (snippet) item.insertText     = new vscode.SnippetString(snippet);
  if (detail)  item.detail         = detail;
  return item;
}

// ─────────────────────────────────────────────────────────────────────────────
// Completion provider
// ─────────────────────────────────────────────────────────────────────────────

function buildCompletionProvider() {
  return {
    provideCompletionItems(document, position /*, token, context */) {
      const line   = document.lineAt(position).text;
      const prefix = line.substring(0, position.character);
      const items  = [];

      // ── After "use ", suggest modules ─────────────────────────────────────
      if (/\buse\s+$/.test(prefix)) {
        for (const m of MODULES) {
          items.push(makeItem(m.label, CIK.Module, m.doc, m.snippet));
        }
        return items;
      }

      // ── After "->", suggest pipeline stages ───────────────────────────────
      if (/->[ \t]*$/.test(prefix)) {
        for (const s of PIPELINE_STAGES) {
          const it = makeItem(s.label, CIK.Function, s.doc, s.snippet, `-> ${s.snippet.split('\n')[0]}`);
          it.sortText = '0' + s.label;   // stages first when triggered
          items.push(it);
        }
        return items;
      }

      // ── After ":=", suggest source keywords ───────────────────────────────
      if (/:=[ \t]*$/.test(prefix)) {
        for (const src of SOURCE_KEYWORDS) {
          items.push(makeItem(src.label, CIK.Function, src.doc, src.snippet, src.snippet));
        }
      }

      // ── Always: keywords ──────────────────────────────────────────────────
      for (const kw of KEYWORDS) {
        items.push(makeItem(kw.label, kw.kind, kw.doc, kw.snippet, kw.detail));
      }

      // ── Always: pipeline stages ───────────────────────────────────────────
      for (const s of PIPELINE_STAGES) {
        items.push(makeItem(s.label, CIK.Function, s.doc, s.snippet));
      }

      // ── Always: source keywords ───────────────────────────────────────────
      for (const src of SOURCE_KEYWORDS) {
        items.push(makeItem(src.label, CIK.Function, src.doc, src.snippet));
      }

      // ── Always: built-in types ────────────────────────────────────────────
      for (const t of TYPES) {
        items.push(makeItem(t, CIK.Class, `pep# built-in type \`${t}\``));
      }

      return items;
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Hover provider
// ─────────────────────────────────────────────────────────────────────────────

function buildHoverProvider() {
  return {
    provideHover(document, position /*, token */) {
      // Try operator tokens first (longer matches before single chars)
      const opRange = document.getWordRangeAtPosition(position, /->|:=|=>/);
      if (opRange) {
        const tok = document.getText(opRange);
        const doc = HOVER_DOCS[tok];
        if (doc) return new vscode.Hover(new vscode.MarkdownString(doc));
      }

      // Word tokens
      const range = document.getWordRangeAtPosition(position, /[a-zA-Z_][a-zA-Z0-9_]*/);
      if (!range) return null;
      const word = document.getText(range);
      const doc  = HOVER_DOCS[word];
      if (!doc) return null;
      return new vscode.Hover(new vscode.MarkdownString(doc));
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Run / watch commands
// ─────────────────────────────────────────────────────────────────────────────

function getExecutable(config) {
  return (config.get('executablePath') || 'pep').trim();
}

function runInTerminal(name, cmd) {
  const terminal = vscode.window.createTerminal({ name });
  terminal.show(true);
  terminal.sendText(cmd, true);
}

function registerCommands(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('pep.runFile', () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage('pep#: No active file.');
        return;
      }
      const file = editor.document.fileName;
      if (!file.endsWith('.pep')) {
        vscode.window.showWarningMessage('pep#: Active file is not a .pep script.');
        return;
      }
      const exe = getExecutable(vscode.workspace.getConfiguration('pep'));
      runInTerminal('pep# run', `${exe} run "${file}"`);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('pep.watchPipeline', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const file = editor.document.fileName;
      const name = await vscode.window.showInputBox({
        prompt: 'Pipeline variable name to watch',
        placeHolder: 'sales',
      });
      if (!name) return;
      const exe = getExecutable(vscode.workspace.getConfiguration('pep'));
      runInTerminal('pep# watch', `${exe} watch "${file}" --pipeline ${name}`);
    })
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Status bar item
// ─────────────────────────────────────────────────────────────────────────────

function createStatusBar(context) {
  const bar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  bar.text        = '$(play) pep#';
  bar.tooltip     = 'Run pep# file';
  bar.command     = 'pep.runFile';
  bar.backgroundColor = undefined;
  context.subscriptions.push(bar);

  function updateBar() {
    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.languageId === 'pep') {
      bar.show();
    } else {
      bar.hide();
    }
  }

  context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(updateBar));
  updateBar();
}

// ─────────────────────────────────────────────────────────────────────────────
// Activation / deactivation
// ─────────────────────────────────────────────────────────────────────────────

function activate(context) {
  // Completion
  context.subscriptions.push(
    vscode.languages.registerCompletionItemProvider(
      { language: 'pep', scheme: 'file' },
      buildCompletionProvider(),
      ' ', '>', '=' , '.'
    )
  );

  // Hover docs
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(
      { language: 'pep', scheme: 'file' },
      buildHoverProvider()
    )
  );

  // Commands
  registerCommands(context);

  // Status bar
  createStatusBar(context);

  console.log('[pep#] extension activated');
}

function deactivate() {
  console.log('[pep#] extension deactivated');
}

module.exports = { activate, deactivate };
