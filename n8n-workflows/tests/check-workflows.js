#!/usr/bin/env node
'use strict';

// Static checks over the workflow JSONs. Every rule here exists because the
// defect it catches already shipped: n8n reports a green execution for all of
// them, so nothing but a check like this notices.
//
//   node n8n-workflows/tests/check-workflows.js            # all workflows
//   node n8n-workflows/tests/check-workflows.js reprogramar # substring filter
//
// Exits non-zero on the first failing rule so it can gate a commit.

const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..');
const filter = process.argv[2];

const HTTP = 'n8n-nodes-base.httpRequest';
const CODE = 'n8n-nodes-base.code';

// Fields that identify the conversation. They come from the parsed command and
// are NOT present on an HTTP response item, which replaces the incoming one.
const STATE_FIELDS = ['chat_id', 'turno_id', 'nueva_fecha', 'nuevo_slot', 'hora_inicio_nueva'];

// Telegram rejects the whole button above this. Silently.
const CALLBACK_LIMIT = 64;
// Longest turno id the system could plausibly emit, for worst-case budgeting.
const WORST_ID = '12345678';

const failures = [];
const notes = [];

function fail(rule, wf, node, detail) {
  failures.push({ rule, wf, node, detail });
}

function loadWorkflows() {
  return fs
    .readdirSync(DIR)
    .filter((f) => f.endsWith('.json'))
    .filter((f) => !filter || f.includes(filter))
    .map((f) => ({ file: f, wf: JSON.parse(fs.readFileSync(path.join(DIR, f), 'utf8')) }));
}

// Immediate predecessors of each node, from the connection graph.
function predecessors(wf) {
  const preds = {};
  for (const [src, out] of Object.entries(wf.connections || {})) {
    for (const branch of out.main || []) {
      for (const conn of branch || []) {
        (preds[conn.node] = preds[conn.node] || []).push(src);
      }
    }
  }
  return preds;
}

function nodeByName(wf, name) {
  return wf.nodes.find((n) => n.name === name);
}

// ---------------------------------------------------------------------------
// RULE 1 — every emitted callback_data fits Telegram's 64-byte budget
// ---------------------------------------------------------------------------
// A callback_data value is usually a concatenation of quoted literals and
// expressions. Reading only the first literal is not enough: the sentinel that
// broke reprogramar (`:slot:none`) lived in the LAST one, and a prefix ending in
// ':' looks like a sentinel when read alone. So capture the whole expression up
// to the end of the button object, then split it into its parts.
function extractCallbackExpressions(blob) {
  const out = [];
  const KEY = 'callback_data:';
  let i = 0;
  while ((i = blob.indexOf(KEY, i)) !== -1) {
    let j = i + KEY.length;
    let depth = 0;
    let quote = null;
    let expr = '';
    while (j < blob.length) {
      const ch = blob[j];
      if (quote) {
        if (ch === quote && blob[j - 1] !== '\\') quote = null;
      } else if (ch === "'" || ch === '"') {
        quote = ch;
      } else if (ch === '(' || ch === '[') {
        depth += 1;
      } else if (ch === ')' || ch === ']') {
        if (depth === 0) break;
        depth -= 1;
      } else if ((ch === ',' || ch === '}') && depth === 0) {
        break;
      }
      expr += ch;
      j += 1;
    }
    out.push(expr.trim());
    i = j;
  }
  return out;
}

function collectCallbacks(wf) {
  const found = [];
  for (const node of wf.nodes) {
    const blob = JSON.stringify(node.parameters || {});
    for (const expr of extractCallbackExpressions(blob)) {
      // Literal segments, in order. Everything else is an interpolated value.
      const literals = [];
      const litRe = /'([^']*)'|"((?:[^"\\]|\\.)*)"/g;
      let m;
      while ((m = litRe.exec(expr)) !== null) {
        literals.push((m[1] !== undefined ? m[1] : m[2]).replace(/\\"/g, '"'));
      }
      const interpolations = (expr.match(/\+/g) || []).length - Math.max(literals.length - 1, 0);
      // Budget each interpolated value at the longest id the system can emit.
      const worst = literals.join('') + WORST_ID.repeat(Math.max(interpolations, 0));
      found.push({ node: node.name, expr, literals, worst });
    }
  }
  return found;
}

function ruleCallbackBudget(file, wf) {
  for (const cb of collectCallbacks(wf)) {
    const size = Buffer.byteLength(cb.worst);
    if (size > CALLBACK_LIMIT) {
      fail('callback-budget', file, cb.node, `"${cb.worst}" = ${size} bytes (limite ${CALLBACK_LIMIT})`);
    }
  }
}

// ---------------------------------------------------------------------------
// RULE 2 — a Code node downstream of an HTTP node must not read conversation
// state off the HTTP item. The response replaces the item; those fields are
// undefined and the message silently loses its destination.
// ---------------------------------------------------------------------------
function ruleNamedNodeReads(file, wf) {
  const preds = predecessors(wf);
  for (const node of wf.nodes) {
    if (node.type !== CODE) continue;
    const parents = preds[node.name] || [];
    const afterHttp = parents.some((p) => (nodeByName(wf, p) || {}).type === HTTP);
    if (!afterHttp) continue;

    const code = (node.parameters || {}).jsCode || '';
    // Strip comments so prose about the defect does not trip the check.
    const bare = code.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');

    for (const field of STATE_FIELDS) {
      // `input.<field>` where `input` came from the HTTP item.
      const direct = new RegExp('\\binput\\.' + field + '\\b').test(bare);
      const raw = new RegExp('\\$json\\.' + field + '\\b').test(bare);
      if (direct || raw) {
        fail(
          'named-node-reads',
          file,
          node.name,
          `lee "${field}" del item HTTP; debe venir de $('Code - Decidir Paso')`
        );
      }
    }
  }
}

// ---------------------------------------------------------------------------
// RULE 3 — flags on the HTTP nodes that talk to the backend.
//
// `neverError` is required on all of them, no exceptions: without it a 404 or a
// 500 throws, the formatter downstream never runs, and the patient gets silence
// instead of a message.
//
// `fullResponse` is required only when something downstream actually reads
// `statusCode` or `.body`. It is NOT universally right: a node whose consumer
// reads the split items of a bare JSON array (the pattern in
// sub-flujo-crear-turno's `Code - Verificar Slots`) is correct without it, and
// demanding it there would be cargo cult.
// ---------------------------------------------------------------------------
function descendantCode(wf, start) {
  const seen = new Set([start]);
  const queue = [start];
  const out = [];
  while (queue.length) {
    const cur = queue.shift();
    for (const branch of ((wf.connections || {})[cur] || {}).main || []) {
      for (const conn of branch || []) {
        if (seen.has(conn.node)) continue;
        seen.add(conn.node);
        const n = nodeByName(wf, conn.node);
        if (n && n.type === CODE) out.push(n);
        queue.push(conn.node);
      }
    }
  }
  return out;
}

function ruleHttpFlags(file, wf) {
  for (const node of wf.nodes) {
    if (node.type !== HTTP) continue;
    const p = node.parameters || {};
    const url = p.url || '';
    if (!/backend:8000|\/turnos|\/profesional/.test(url)) continue; // Telegram sends are exempt
    const resp = ((p.options || {}).response || {}).response || {};

    if (resp.neverError !== true) {
      fail('http-flags', file, node.name, 'sin neverError: un 404 o un 500 tira excepcion y el paciente recibe silencio');
    }

    const consumers = descendantCode(wf, node.name);
    const readsWrapped = consumers.some((c) =>
      /\bstatusCode\b|\.body\b/.test((c.parameters || {}).jsCode || '')
    );
    if (readsWrapped && resp.fullResponse !== true) {
      fail(
        'http-flags',
        file,
        node.name,
        'un Code aguas abajo lee statusCode/.body pero falta fullResponse: esas ramas son codigo muerto'
      );
    }
  }
}

// ---------------------------------------------------------------------------
// RULE 4 — no button may emit a callback whose payload is a sentinel the flow
// then treats as a real value. `slot:none` produced a PUT with the literal
// string "none" as the new time.
// ---------------------------------------------------------------------------
// A trailing ':' is fine — it is a prefix awaiting an interpolated value. What
// is not fine is a hardcoded word sitting in a data position, because the parser
// reads it as if the patient had chosen it.
const SENTINELS = /:(none|null|undefined|nan|na|tbd)\b/i;

function ruleHonorableCallbacks(file, wf) {
  for (const cb of collectCallbacks(wf)) {
    const assembled = cb.literals.join('');
    const hit = assembled.match(SENTINELS);
    if (hit) {
      fail(
        'honorable-callbacks',
        file,
        cb.node,
        `"${assembled}" pone "${hit[1]}" en posicion de dato; el parser lo lee como un valor elegido por el paciente`
      );
    }
  }
}

// ---------------------------------------------------------------------------
// RULE 5 — every sendMessage payload must build a valid Telegram message.
// ---------------------------------------------------------------------------
function ruleSendMessagePayloads(file, wf) {
  for (const node of wf.nodes) {
    const p = node.parameters || {};
    if (!p.jsonBody || !/sendMessage/.test(p.url || '')) continue;
    const inner = p.jsonBody.replace(/^=\{\{/, '').replace(/\}\}$/, '');
    try {
      new Function('$json', '$env', 'return ' + inner);
    } catch (e) {
      fail('sendmessage-payload', file, node.name, 'expresion invalida: ' + e.message);
    }
    if (inner.includes('}}') || inner.includes('{{')) {
      fail('sendmessage-payload', file, node.name, 'colision de delimitadores: separa las llaves con un espacio');
    }
  }
}

// ---------------------------------------------------------------------------
// RULE 6 — structural sanity: graph reachable, expressions prefixed, jsCode parses
// ---------------------------------------------------------------------------
function ruleStructure(file, wf) {
  const names = new Set(wf.nodes.map((n) => n.name));
  for (const [src, out] of Object.entries(wf.connections || {})) {
    if (!names.has(src)) fail('structure', file, src, 'conexion desde un nodo inexistente');
    for (const branch of out.main || []) {
      for (const conn of branch || []) {
        if (!names.has(conn.node)) fail('structure', file, src, 'conecta a un nodo inexistente: ' + conn.node);
      }
    }
  }

  for (const node of wf.nodes) {
    const code = (node.parameters || {}).jsCode;
    if (code) {
      try {
        new Function(code);
      } catch (e) {
        fail('structure', file, node.name, 'jsCode no parsea: ' + e.message);
      }
    }
    if (((node.parameters || {}).options || {}).reply_markup) {
      fail('structure', file, node.name, 'reply_markup en options: el nodo Telegram lo descarta en silencio');
    }
  }

  // Unreachable nodes: everything must be walkable from an entry point. Entry
  // points are seeded by "has no incoming connection" rather than by node type —
  // `n8n-nodes-base.webhook` is a trigger whose type does not say so.
  const preds = predecessors(wf);
  const entries = wf.nodes.filter((n) => !(preds[n.name] || []).length).map((n) => n.name);
  const seen = new Set(entries);
  const queue = [...entries];
  while (queue.length) {
    const cur = queue.shift();
    for (const branch of ((wf.connections || {})[cur] || {}).main || []) {
      for (const conn of branch || []) {
        if (!seen.has(conn.node)) {
          seen.add(conn.node);
          queue.push(conn.node);
        }
      }
    }
  }
  for (const node of wf.nodes) {
    if (!seen.has(node.name)) fail('structure', file, node.name, 'inalcanzable desde el trigger');
  }
}

// ---------------------------------------------------------------------------

const RULES = [
  ['callback-budget', ruleCallbackBudget],
  ['named-node-reads', ruleNamedNodeReads],
  ['http-flags', ruleHttpFlags],
  ['honorable-callbacks', ruleHonorableCallbacks],
  ['sendmessage-payload', ruleSendMessagePayloads],
  ['structure', ruleStructure],
];

const workflows = loadWorkflows();
if (!workflows.length) {
  console.error('sin workflows que chequear' + (filter ? ' para "' + filter + '"' : ''));
  process.exit(1);
}

for (const { file, wf } of workflows) {
  for (const [, run] of RULES) run(file, wf);
}

const byRule = {};
for (const f of failures) (byRule[f.rule] = byRule[f.rule] || []).push(f);

for (const [name] of RULES) {
  const hits = byRule[name] || [];
  if (!hits.length) {
    console.log('  ok    ' + name);
    continue;
  }
  console.log('  FAIL  ' + name + '  (' + hits.length + ')');
  for (const h of hits) console.log('          ' + h.wf + ' :: ' + h.node + '\n            ' + h.detail);
}

for (const n of notes) console.log('  nota  ' + n);
console.log('\n' + workflows.length + ' workflow(s), ' + failures.length + ' problema(s)');
process.exit(failures.length ? 1 : 0);
