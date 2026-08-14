#!/usr/bin/env node
'use strict';

// Executes the Code nodes of sub-flujo-reprogramar-turno against simulated data.
// The static checks prove shape; this proves behaviour — including the round
// trip, which is the one that would have caught the `slot:none` chain: every
// callback_data the flow emits is fed back into its own parser and must resolve
// to the step it was meant to reach, carrying usable data.
//
//   node n8n-workflows/tests/check-reprogramar-behavior.js

const fs = require('fs');
const path = require('path');

const wf = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'sub-flujo-reprogramar-turno.json'), 'utf8')
);

const code = (name) => wf.nodes.find((n) => n.name === name).parameters.jsCode;

// Runs a Code node. `items` is what $input.all() returns; `named` maps node
// names to the json their $('...') lookup should yield.
function run(nodeName, items, named) {
  const $input = { all: () => items };
  const $ = (name) => ({
    first: () => {
      if (!named || !(name in named)) throw new Error('node not found: ' + name);
      return { json: named[name] };
    },
  });
  return new Function('$input', '$', code(nodeName))($input, $)[0].json;
}

const decidir = (text, chatId) => run('Code - Decidir Paso', [{ json: { chat_id: chatId || 555, text } }], {});

const httpItem = (statusCode, body) => [{ json: { statusCode, body } }];

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

function section(title) {
  console.log('\n' + title);
}

// ---------------------------------------------------------------------------
section('Parser — vocabulario');

const P = {
  listar: decidir('cmd:reprogramar'),
  fechas: decidir('cmd:reprogramar:t:7'),
  horarios: decidir('cmd:reprogramar:t:7:f:2026-08-20'),
  confirmar: decidir('cmd:reprogramar:t:7:f:2026-08-20:h:10:00'),
  ejecutar: decidir('cmd:reprogramar:ok:7:2026-08-20:10:00'),
  legacy: decidir('cmd:reprogramar:turno_id:7'),
};

check('cmd:reprogramar -> listar', P.listar.accion === 'listar');
check('t:<id> -> fechas', P.fechas.accion === 'fechas' && P.fechas.turno_id === '7');
check('t:<id>:f:<fecha> -> horarios', P.horarios.accion === 'horarios' && P.horarios.fecha === '2026-08-20');
check(
  't:<id>:f:<fecha>:h:<hora> -> confirmar',
  P.confirmar.accion === 'confirmar' && P.confirmar.hora === '10:00',
  JSON.stringify(P.confirmar)
);
check(
  'ok:<id>:<fecha>:<hora> -> ejecutar',
  P.ejecutar.accion === 'ejecutar' && P.ejecutar.turno_id === '7' && P.ejecutar.fecha === '2026-08-20' && P.ejecutar.hora === '10:00',
  JSON.stringify(P.ejecutar)
);
check(
  'D3b: la forma del recordatorio (turno_id:<id>) cae en fechas',
  P.legacy.accion === 'fechas' && P.legacy.turno_id === '7',
  JSON.stringify(P.legacy)
);

section('Parser — degradacion');
check('un ID tipeado no entra en ninguna accion', decidir('/reprogramar 42').accion === 'listar');
check('texto libre degrada a listar', decidir('hola que tal').accion === 'listar');
check('callback desconocido degrada a listar', decidir('cmd:reprogramar:zz:1').accion === 'listar');
check('el sentinel viejo ya no produce ejecutar', decidir('cmd:reprogramar:turno_id:7:fecha:2026-08-20:slot:none').accion === 'listar');
check('turno_id vacio degrada a listar', decidir('cmd:reprogramar:t:').accion === 'listar');

// ---------------------------------------------------------------------------
section('Listar');

const DEC = { 'Code - Decidir Paso': { chat_id: 555, turno_id: '7', fecha: '2026-08-20', hora: '10:00' } };

const listaOk = run(
  'Code - Formatear Lista',
  httpItem(200, [
    { id: 7, fecha: '2026-08-20', hora_inicio: '10:00:00' },
    { id: 9, fecha: '2026-08-22', hora_inicio: '09:30:00' },
  ]),
  DEC
);
check('lista con turnos: un boton por turno', listaOk.cantidad === 2 && listaOk.inline_keyboard.length === 2);
check('lista: el chat_id sale del nodo nombrado', listaOk.chat_id === 555);
check('lista: no muestra el id en el texto', !/\b7\b/.test(listaOk.inline_keyboard[0][0].text), listaOk.inline_keyboard[0][0].text);

const listaVacia = run('Code - Formatear Lista', httpItem(200, []), DEC);
check('lista vacia: mensaje propio', /no tenes turnos/i.test(listaVacia.mensaje), listaVacia.mensaje);
check('lista vacia: ofrece reservar', listaVacia.inline_keyboard[0][0].callback_data === 'cmd:crear');

const listaError = run('Code - Formatear Lista', httpItem(422, { detail: 'boom' }), DEC);
check(
  'un 422 NO se confunde con lista vacia',
  listaError.mensaje !== listaVacia.mensaje && /no pudimos/i.test(listaError.mensaje),
  listaError.mensaje
);

// ---------------------------------------------------------------------------
section('Fechas');

const fechas = run('Code - Formatear Fechas', [{ json: {} }], DEC);
const botonesFecha = fechas.inline_keyboard.filter((r) => /:f:/.test(r[0].callback_data));
check('ofrece 7 fechas', botonesFecha.length === 7, 'fueron ' + botonesFecha.length);

function hoyAr() {
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Argentina/Buenos_Aires',
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date());
  return p.find((x) => x.type === 'year').value + '-' + p.find((x) => x.type === 'month').value + '-' + p.find((x) => x.type === 'day').value;
}
function addDays(s, n) {
  const p = s.split('-').map(Number);
  const d = new Date(Date.UTC(p[0], p[1] - 1, p[2]));
  d.setUTCDate(d.getUTCDate() + n);
  return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0') + '-' + String(d.getUTCDate()).padStart(2, '0');
}

const hoy = hoyAr();
const primera = botonesFecha[0][0].callback_data.split(':f:')[1];
check('la ventana arranca manana (hora local AR)', primera === addDays(hoy, 1), primera + ' vs ' + addDays(hoy, 1));
check('no ofrece hoy', !botonesFecha.some((r) => r[0].callback_data.endsWith(hoy)));

// Defecto 7: la etiqueta se deriva de la fecha, no del indice.
const etiquetaPrimera = botonesFecha[0][0].text;
check('la etiqueta del primer boton dice Manana, no Hoy', /Manana/.test(etiquetaPrimera), etiquetaPrimera);
for (const row of botonesFecha) {
  const fechaEnCallback = row[0].callback_data.split(':f:')[1];
  if (/\(/.test(row[0].text)) {
    const fechaEnTexto = row[0].text.match(/\(([^)]+)\)/)[1];
    if (fechaEnTexto !== fechaEnCallback) {
      check('etiqueta coincide con su fecha: ' + row[0].text, false, fechaEnTexto + ' != ' + fechaEnCallback);
    }
  }
}
check('todas las etiquetas coinciden con su fecha', true);
check('ofrece volver a la lista', fechas.inline_keyboard.some((r) => r[0].callback_data === 'cmd:reprogramar'));

// Defecto 8: la fecha se resuelve en hora local del profesional, no en la del
// proceso. No se puede probar cambiando TZ (el helper pasa el timeZone explícito
// a Intl, y el shell de Windows no propaga la variable), así que se prueba sobre
// un instante elegido: 01:00 UTC es el día anterior en Argentina.
section('Timezone');

const fmtSrc = code('Code - Formatear Fechas').match(/function fmtArgentina[\s\S]*?\n\}/)[0];
const fmtArgentina = new Function(fmtSrc + '; return fmtArgentina;')();
const instante = new Date('2026-08-14T01:00:00Z'); // 2026-08-13 22:00 en AR (UTC-3)

check(
  'fmtArgentina resuelve el dia local, no el UTC',
  fmtArgentina(instante) === '2026-08-13',
  'dio ' + fmtArgentina(instante)
);
check(
  'y difiere de toISOString, que es como estaba escrito',
  instante.toISOString().slice(0, 10) === '2026-08-14' && fmtArgentina(instante) === '2026-08-13'
);

// ---------------------------------------------------------------------------
section('Horarios');

const slotsOk = run(
  'Code - Formatear Slots',
  httpItem(200, [
    { hora_inicio: '10:00', hora_fin: '10:30', disponible: true },
    { hora_inicio: '11:00', hora_fin: '11:30', disponible: true },
  ]),
  DEC
);
check('array pelado bajo body: lee los slots', slotsOk.cantidad === 2, JSON.stringify(slotsOk.cantidad));
check('un boton por slot mas el de cambiar fecha', slotsOk.inline_keyboard.length === 3);

const slotsVacio = run('Code - Formatear Slots', httpItem(200, []), DEC);
check('sin horarios: ofrece cambiar de fecha', slotsVacio.inline_keyboard[0][0].callback_data === 'cmd:reprogramar:t:7');
check(
  'sin horarios: ningun callback con centinela',
  !JSON.stringify(slotsVacio.inline_keyboard).includes('none'),
  JSON.stringify(slotsVacio.inline_keyboard)
);

const slotsError = run('Code - Formatear Slots', httpItem(500, {}), DEC);
check('500 en disponibilidad: no dice "no quedan horarios"', !/no quedan/i.test(slotsError.mensaje), slotsError.mensaje);

// ---------------------------------------------------------------------------
section('Confirmacion');

const confVigente = run(
  'Code - Preparar Confirmacion',
  httpItem(200, [{ id: 7, fecha: '2026-08-18', hora_inicio: '09:00:00' }]),
  DEC
);
check('turno vigente: pide confirmacion', confVigente.vigente === true);
check('muestra el turno viejo y el nuevo', /De: /.test(confVigente.mensaje) && /A: /.test(confVigente.mensaje), confVigente.mensaje);
check('el boton de confirmar emite ok:', /^cmd:reprogramar:ok:7:2026-08-20:10:00$/.test(confVigente.inline_keyboard[0][0].callback_data), confVigente.inline_keyboard[0][0].callback_data);

const confCancelado = run('Code - Preparar Confirmacion', httpItem(200, [{ id: 99, fecha: '2026-08-18', hora_inicio: '09:00:00' }]), DEC);
check('turno que desaparecio entre el boton y el toque: se detecta', confCancelado.vigente === false);

// ---------------------------------------------------------------------------
section('Resultado');

const r200 = run('Code - Formatear Resultado', httpItem(200, { id: 7, fecha: '2026-08-20', hora_inicio: '10:00:00' }), DEC);
check('200: exito', r200.exito === true);
check('200: nombra el turno con body.id, no undefined', r200.turno_id === 7 && !/undefined/.test(r200.mensaje), r200.mensaje);

const r404 = run('Code - Formatear Resultado', httpItem(404, { detail: 'no existe' }), DEC);
check('404: fallo', r404.exito === false && /no encontramos/i.test(r404.mensaje), r404.mensaje);

const r409 = run('Code - Formatear Resultado', httpItem(409, { detail: 'ocupado' }), DEC);
check('409: fallo y ofrece otro horario', r409.exito === false && /ya fue tomado/i.test(r409.mensaje));

const r422 = run('Code - Formatear Resultado', httpItem(422, { detail: 'validation' }), DEC);
check('422 NO se reporta como exito', r422.exito === false, r422.mensaje);

const rSinStatus = run('Code - Formatear Resultado', [{ json: { body: {} } }], DEC);
check('status ausente se trata como fallo (D5)', rSinStatus.exito === false, rSinStatus.mensaje);
check('un fallo nunca dice que el turno se movio', [r404, r409, r422, rSinStatus].every((r) => !/quedo para/i.test(r.mensaje)));

// ---------------------------------------------------------------------------
section('Round trip — todo callback que el flujo emite, su propio parser lo entiende');

const EMITIDOS = []
  .concat(listaOk.inline_keyboard, listaVacia.inline_keyboard, listaError.inline_keyboard)
  .concat(fechas.inline_keyboard)
  .concat(slotsOk.inline_keyboard, slotsVacio.inline_keyboard, slotsError.inline_keyboard)
  .concat(confVigente.inline_keyboard, confCancelado.inline_keyboard)
  .concat(r200.inline_keyboard, r404.inline_keyboard, r409.inline_keyboard, rSinStatus.inline_keyboard)
  .map((row) => row[0].callback_data);

const AJENOS = ['cmd:crear', 'cmd:menu']; // los resuelve el orquestador, no este flujo
let roundTripBad = 0;
for (const cb of new Set(EMITIDOS)) {
  const bytes = Buffer.byteLength(cb);
  if (bytes > 64) {
    check('presupuesto: ' + cb, false, bytes + ' bytes');
    roundTripBad += 1;
    continue;
  }
  if (AJENOS.includes(cb)) continue;
  const parsed = decidir(cb);
  const esperado = cb === 'cmd:reprogramar' ? 'listar' : null;
  if (esperado && parsed.accion !== esperado) {
    check('round trip ' + cb, false, 'accion=' + parsed.accion);
    roundTripBad += 1;
  } else if (!esperado && parsed.accion === 'listar') {
    check('round trip ' + cb, false, 'el parser no lo reconoce, degrada a listar');
    roundTripBad += 1;
  }
}
check('los ' + new Set(EMITIDOS).size + ' callbacks emitidos son entendidos por el parser', roundTripBad === 0);

console.log('\nchecks: ' + checks + '  failures: ' + failures);
process.exit(failures ? 1 : 0);
