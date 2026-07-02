const input = ($input.all()[0] && $input.all()[0].json) || {};

let text = '';
let chatId = null;
let callbackQueryId = null;
let isCallback = false;

if (input.message) {
  text = input.message.text || '';
  chatId = input.message.chat && input.message.chat.id;
} else if (input.callback_query) {
  text = input.callback_query.data || '';
  chatId = input.callback_query.message && input.callback_query.message.chat && input.callback_query.message.chat.id;
  callbackQueryId = input.callback_query.id;
  isCallback = true;
}

const textLower = String(text || '').toLowerCase().trim();
let comando = 'desconocido';
const payload = {};

// --- Botones del mensaje de bienvenida ---
if (textLower === 'cmd:crear' || textLower === 'cmd:reservar') {
  comando = 'crear';
} else if (textLower === 'cmd:cancelar') {
  comando = 'cancelar';
} else if (textLower === 'cmd:reprogramar') {
  comando = 'reprogramar';
} else if (textLower === 'cmd:mis_turnos') {
  comando = 'mis_turnos';
}
// --- Callbacks de los sub-workflows ---
// cmd:reprogramar:turno_id:N:fecha:YYYY-MM-DD:slot:HH:MM
else if (textLower.startsWith('cmd:reprogramar:turno_id:')) {
  comando = 'reprogramar';
  const parts = textLower.split(':');
  for (let i = 0; i < parts.length - 1; i += 2) {
    const key = parts[i];
    const value = parts[i + 1];
    if (key === 'turno_id') payload.turno_id = value;
    if (key === 'fecha') payload.fecha = value;
    if (key === 'slot') payload.slot = value;
  }
}
// cmd:crear:slot:HH:MM
else if (textLower.startsWith('cmd:crear:slot:')) {
  comando = 'crear';
  const parts = textLower.split(':');
  payload.slot = parts[2];
  payload.minutos = parts[3] || '00';
}
// cmd:cancelar:turno_id:N
else if (textLower.startsWith('cmd:cancelar:turno_id:')) {
  comando = 'cancelar';
  payload.turno_id = textLower.split(':')[2];
}
// --- Comandos textuales (compatibilidad) ---
else if (textLower.startsWith('/reservar') || textLower === 'reservar' || textLower.includes('quiero un turno') || textLower.includes('sacar turno')) {
  comando = 'crear';
} else if (textLower.startsWith('/cancelar') || textLower === 'cancelar' || textLower.includes('dar de baja')) {
  comando = 'cancelar';
} else if (textLower.startsWith('/reprogramar') || textLower === 'reprogramar' || textLower.includes('cambiar turno') || textLower.includes('mover turno')) {
  comando = 'reprogramar';
}

return [{
  json: {
    comando: comando,
    chat_id: chatId,
    callback_query_id: callbackQueryId,
    is_callback: isCallback,
    text: text,
    payload: payload
  }
}];
