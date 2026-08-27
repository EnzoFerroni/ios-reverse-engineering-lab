// cripto_observa.js — Observacao de uso de APIs criptograficas (iOS)
// Intercepta CCCrypt (CommonCrypto) para evidenciar operacoes de cifra/decifra
// e o algoritmo/operacao usados. Observacao apenas. Finalidade academica.

'use strict';

// Compat Frida 17+: carrega o bridge ObjC (global removido no 17).
var __b = (typeof globalThis.ObjC !== 'undefined') ? globalThis.ObjC : require('frida-objc-bridge');
var ObjC = (__b && __b.default) ? __b.default : __b;
// Compat Frida 17: Module.findExportByName foi removido.
function findExport(mod, name) {
  if (typeof Module.findExportByName === 'function') return findExport(mod, name);
  try { if (mod) { var m = Process.getModuleByName(mod); return m ? m.findExportByName(name) : null; } } catch (e) {}
  return (typeof Module.findGlobalExportByName === 'function') ? Module.findGlobalExportByName(name) : null;
}


function emit(tipo, extra) {
  var msg = { tecnica: 'cripto', tipo: tipo, t: Date.now() };
  if (extra) { for (var k in extra) { msg[k] = extra[k]; } }
  send(msg);
}

// Mapeia constantes do CommonCryptor para leitura humana.
var OP = { 0: 'kCCEncrypt', 1: 'kCCDecrypt' };
var ALG = { 0: 'AES128', 1: 'DES', 2: '3DES', 3: 'CAST', 4: 'RC4', 5: 'RC2', 6: 'Blowfish' };

if (ObjC.available) {
  try {
    var ccCrypt = findExport('libcommonCrypto.dylib', 'CCCrypt') ||
                  findExport(null, 'CCCrypt');
    if (ccCrypt) {
      Interceptor.attach(ccCrypt, {
        onEnter: function (args) {
          var op = OP[args[0].toInt32()] || ('op' + args[0]);
          var alg = ALG[args[1].toInt32()] || ('alg' + args[1]);
          console.log('[CRY] CCCrypt ' + op + ' ' + alg);
          emit('evento', { api: 'CCCrypt', op: op, alg: alg });
        }
      });
      emit('hook_ready');
      console.log('[CRY] Hook CCCrypt instalado.');
    } else {
      emit('erro', { msg: 'CCCrypt nao encontrado' });
    }
  } catch (e) {
    emit('erro', { msg: '' + e });
    console.log('[CRY] Erro: ' + e);
  }
} else {
  emit('erro', { msg: 'Runtime Objective-C indisponivel' });
}
