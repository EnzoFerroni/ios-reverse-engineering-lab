// jailbreak_observa.js — Observacao de verificacoes de jailbreak (iOS)
// Fiel ao Quadro "Trecho de script Frida para monitoramento de jailbreak
// detection" do artigo. Intercepta -[NSFileManager fileExistsAtPath:] para
// OBSERVAR (sem alterar) consultas a indicadores. Mede o instante de cada
// consulta para analisar a sincronizacao inicializacao x verificacao.
//
// IMPORTANTE: este script NAO forja retornos. A discussao de evasao no artigo
// e didatica; para reproduzir o efeito sobre a analise, alterar o retorno e
// uma escolha consciente do experimentador, fora deste script de observacao.

'use strict';

// Compat Frida 17+: carrega o bridge ObjC (global removido no 17).
var __b = (typeof globalThis.ObjC !== 'undefined') ? globalThis.ObjC : require('frida-objc-bridge');
var ObjC = (__b && __b.default) ? __b.default : __b;

function emit(tipo, extra) {
  var msg = { tecnica: 'jailbreak', tipo: tipo, t: Date.now() };
  if (extra) { for (var k in extra) { msg[k] = extra[k]; } }
  send(msg);
}

var INDICADORES = [
  '/Applications/Cydia.app', '/bin/bash', '/etc/apt', '/usr/sbin/sshd',
  '/private/var/lib/apt', '/Library/MobileSubstrate/MobileSubstrate.dylib'
];

if (ObjC.available) {
  try {
    var NSFileManager = ObjC.classes.NSFileManager;
    var method = '- fileExistsAtPath:';

    Interceptor.attach(NSFileManager[method].implementation, {
      onEnter: function (args) {
        this.path = new ObjC.Object(args[2]).toString();
      },
      onLeave: function (retval) {
        if (INDICADORES.indexOf(this.path) >= 0) {
          console.log('[JB] Indicador consultado: ' + this.path +
                      ' (retorno original = ' + retval + ')');
          emit('evento', { api: 'fileExistsAtPath', path: this.path,
                           retorno: retval.toInt32() });
        }
      }
    });

    emit('hook_ready');
    console.log('[JB] Hook instalado; observando consultas a indicadores.');
  } catch (e) {
    emit('erro', { msg: '' + e });
    console.log('[JB] Erro: ' + e);
  }
} else {
  emit('erro', { msg: 'Runtime Objective-C indisponivel' });
}
