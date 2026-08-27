// ssl_inexistente_observa.js — CONTROLE NEGATIVO A.
// Copia fiel de ssl_observa.js com um unico ponto alterado: o seletor da
// NSURLSession foi trocado por '- metodoQueNaoExiste:', que nao existe no
// runtime. O hook nao pode ser instalado e 'hook_ready' nunca e emitido.
// Serve para demonstrar que o harness registra falha quando ela ocorre.
// Este arquivo NAO faz parte da coleta; e instrumento de validacao.

'use strict';

// Compat Frida 17+: o global ObjC foi removido; carrega o bridge.
var __b = (typeof globalThis.ObjC !== 'undefined') ? globalThis.ObjC : require('frida-objc-bridge');
var ObjC = (__b && __b.default) ? __b.default : __b;

function emit(tipo, extra) {
  var msg = { tecnica: 'ssl_inexistente', tipo: tipo, t: Date.now() };
  if (extra) { for (var k in extra) { msg[k] = extra[k]; } }
  send(msg);
}

if (ObjC.available) {
  try {
    var NSURLSession = ObjC.classes.NSURLSession;
    var selector = '- metodoQueNaoExiste:';   // <<< unica diferenca vs ssl_observa.js

    Interceptor.attach(NSURLSession[selector].implementation, {
      onEnter: function () { emit('evento', { api: 'metodoQueNaoExiste' }); }
    });

    emit('hook_ready');
    console.log('[CTRL-A] Hook instalado (NAO deveria acontecer).');
  } catch (e) {
    emit('erro', { msg: '' + e });
    console.log('[CTRL-A] Erro ao instalar hooks: ' + e);
  }
} else {
  emit('erro', { msg: 'Runtime Objective-C indisponivel' });
  console.log('[CTRL-A] Runtime Objective-C indisponivel.');
}
