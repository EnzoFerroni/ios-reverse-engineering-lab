// ssl_observa.js — Observacao de validacao SSL/TLS (iOS, runtime Objective-C)
// Fiel ao Quadro "Trecho de script Frida para observacao de validacao de
// certificado" do artigo. NAO altera retornos; apenas observa requisicoes
// HTTPS para evidenciar a janela de validacao. Finalidade academica.
//
// Emite eventos estruturados via send() para o harness (runner.py) contar
// sucesso e medir o tempo de estabilizacao pos-injecao.

'use strict';

// Compat Frida 17+: o global ObjC foi removido; carrega o bridge.
// Em Frida <=16 o global existe e este require e ignorado.
var __b = (typeof globalThis.ObjC !== 'undefined') ? globalThis.ObjC : require('frida-objc-bridge');
var ObjC = (__b && __b.default) ? __b.default : __b;
// Compat Frida 17: Module.findExportByName foi removido.
function findExport(mod, name) {
  if (typeof Module.findExportByName === 'function') return findExport(mod, name);
  try { if (mod) { var m = Process.getModuleByName(mod); return m ? m.findExportByName(name) : null; } } catch (e) {}
  return (typeof Module.findGlobalExportByName === 'function') ? Module.findGlobalExportByName(name) : null;
}


function emit(tipo, extra) {
  var msg = { tecnica: 'ssl', tipo: tipo, t: Date.now() };
  if (extra) { for (var k in extra) { msg[k] = extra[k]; } }
  send(msg);
}

if (ObjC.available) {
  try {
    var NSURLSession = ObjC.classes.NSURLSession;
    var selector = '- dataTaskWithRequest:completionHandler:';

    Interceptor.attach(NSURLSession[selector].implementation, {
      onEnter: function (args) {
        try {
          var request = new ObjC.Object(args[2]);
          var url = request.URL().absoluteString().toString();
          if (url.indexOf('https') === 0) {
            console.log('[TLS] Requisicao observada: ' + url);
            emit('evento', { api: 'NSURLSession.dataTaskWithRequest', url: url });
          }
        } catch (err) {
          console.log('[TLS] Falha ao ler request: ' + err);
        }
      }
    });

    // Hook complementar de baixo nivel: avaliacao de confianca do Security.framework.
    var SecTrustEvaluate = findExport('Security', 'SecTrustEvaluateWithError');
    if (SecTrustEvaluate) {
      Interceptor.attach(SecTrustEvaluate, {
        onEnter: function () { emit('evento', { api: 'SecTrustEvaluateWithError' }); }
      });
    }

    emit('hook_ready');
    console.log('[TLS] Hooks instalados; aguardando trafego.');
  } catch (e) {
    emit('erro', { msg: '' + e });
    console.log('[TLS] Erro ao instalar hooks: ' + e);
  }
} else {
  emit('erro', { msg: 'Runtime Objective-C indisponivel' });
  console.log('[TLS] Runtime Objective-C indisponivel.');
}
