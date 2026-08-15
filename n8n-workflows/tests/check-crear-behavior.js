#!/usr/bin/env node
'use strict';

// Ejecuta `Code - Verificar Slots` de sub-flujo-crear-turno con datos simulados.
//
// El caso que motiva este harness: el nodo HTTP no declaraba `neverError`, así
// que un 500 del backend tiraba excepción y el paciente recibía silencio. Y
// agregar el flag sin más lo hacía peor de otra forma — el error llegaba como
// cero slots, el flujo reintentaba 7 días y terminaba diciendo "no encontramos
// turnos disponibles" sobre un backend caído.
//
//   node n8n-workflows/tests/check-crear-behavior.js

const fs = require('fs');
const path = require('path');

const wf = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'sub-flujo-crear-turno.json'), 'utf8')
);

const code = (name) => wf.nodes.find((n) => n.name === name).parameters.jsCode;

function verificarSlots(httpJson, decidido, staticData) {
  const $input = { all: () => [{ json: httpJson }] };
  const $ = () => ({ first: () => ({ json: decidido }) });
  const $getWorkflowStaticData = () => staticData;
  return new Function(
    '$input',
    '$',
    '$getWorkflowStaticData',
    code('Code - Verificar Slots')
  )($input, $, $getWorkflowStaticData)[0].json;
}

const DECIDIDO = { chat_id: 555, fecha: '2026-08-20', fecha_inicio: '2026-08-20' };
const slot = (h) => ({ hora_inicio: h, hora_fin: h, disponible: true });

let failures = 0;
let checks = 0;

function check(label, cond, detail) {
  checks += 1;
  if (cond) {
    console.log('  ok    ' + label);
  } else {
    failures += 1;
    console.log('  FAIL  ' + label + (detail ? '\n          ' + detail : ''));
  }
}

console.log('\nAgenda con horarios');
const conSlots = verificarSlots(
  { statusCode: 200, body: [slot('09:00'), slot('09:30')] },
  DECIDIDO,
  {}
);
check('lee el array pelado desde .body', conSlots.decision === 'found', JSON.stringify(conSlots.decision));
check('conserva los slots', (conSlots.slots || []).length === 2);
check('el chat_id sobrevive', conSlots.chat_id === 555);

console.log('\nAgenda vacía (día sin horarios)');
const sinSlots = verificarSlots({ statusCode: 200, body: [] }, DECIDIDO, {});
check(
  'reintenta con el día siguiente en vez de rendirse',
  sinSlots.decision === 'retry',
  JSON.stringify(sinSlots.decision)
);
check('avanza la fecha', sinSlots.fecha && sinSlots.fecha !== DECIDIDO.fecha, sinSlots.fecha);

console.log('\nBackend caído — el caso que motivó todo');
for (const status of [500, 502, 422, 404]) {
  const caido = verificarSlots({ statusCode: status, body: { detail: 'boom' } }, DECIDIDO, {});
  check(
    status + ' NO se confunde con agenda vacía',
    caido.decision === 'error_backend',
    'dio ' + JSON.stringify(caido.decision)
  );
  check(status + ' no dispara el loop de reintento', caido.decision !== 'retry');
  check(status + ' conserva el chat_id para poder avisar', caido.chat_id === 555);
}

console.log('\nRespuesta sin status reconocible');
const sinStatus = verificarSlots({ body: [] }, DECIDIDO, {});
check(
  'se trata como fallo, no como agenda vacía',
  sinStatus.decision === 'error_backend',
  JSON.stringify(sinStatus.decision)
);

console.log('\nRuteo del Switch');
const sw = wf.nodes.find((n) => n.name === 'Switch - Found');
const claves = (sw.parameters.rules.values || []).map((v) => v.outputKey);
const salidas = wf.connections['Switch - Found'].main;
check('el switch conoce error_backend', claves.includes('error_backend'), claves.join(', '));
check(
  'cada decisión tiene su propia salida',
  salidas.length === claves.length + 1,
  salidas.length + ' salidas para ' + claves.length + ' reglas + fallback'
);
const destino = (i) => (salidas[i] || []).map((c) => c.node).join(',');
check(
  'error_backend NO cae en "No Hay Turnos"',
  destino(claves.indexOf('error_backend')) !== destino(claves.length),
  destino(claves.indexOf('error_backend')) + ' vs ' + destino(claves.length)
);
check(
  'el fallback sigue llevando a "No Hay Turnos"',
  /No Hay Turnos/.test(destino(claves.length)),
  destino(claves.length)
);

console.log('\nchecks: ' + checks + '  failures: ' + failures);
process.exit(failures ? 1 : 0);
