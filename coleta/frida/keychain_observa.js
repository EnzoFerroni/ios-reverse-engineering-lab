// keychain_observa.js — Observacao de uso do Keychain (iOS)
// Intercepta as APIs do Security.framework (SecItemAdd / SecItemCopyMatching)
// para evidenciar gravacao e leitura de itens sensiveis. Observacao apenas;
// nao modifica parametros nem retornos. Finalidade academica.

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
  var msg = { tecnica: 'keychain', tipo: tipo, t: Date.now() };
  if (extra) { for (var k in extra) { msg[k] = extra[k]; } }
  send(msg);
}

if (ObjC.available) {
  try {
    var alvos = ['SecItemAdd', 'SecItemCopyMatching', 'SecItemUpdate', 'SecItemDelete'];
    var instalados = 0;

    alvos.forEach(function (nome) {
      var ptr = findExport('Security', nome);
      if (ptr) {
        Interceptor.attach(ptr, {
          onEnter: function () {
            console.log('[KC] ' + nome + ' chamada');
            emit('evento', { api: nome });
          }
        });
        instalados++;
      }
    });

    if (instalados > 0) {
      emit('hook_ready');
      console.log('[KC] ' + instalados + ' hooks de Keychain instalados.');
    } else {
      emit('erro', { msg: 'Nenhum simbolo de Keychain encontrado' });
    }
  } catch (e) {
    emit('erro', { msg: '' + e });
    console.log('[KC] Erro: ' + e);
  }
} else {
  emit('erro', { msg: 'Runtime Objective-C indisponivel' });
}
