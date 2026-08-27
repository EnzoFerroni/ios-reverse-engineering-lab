// combo_observa.js — observa varias APIs sensiveis ao mesmo tempo (keychain,
// cripto, transporte, storage). Para coleta dirigida por usuario no iGoat.
var __b=require('frida-objc-bridge'); var ObjC=__b.default||__b;
function fx(m,n){ if(typeof Module.findExportByName==='function') return Module.findExportByName(m,n);
  try{var x=Process.getModuleByName(m); return x?x.findExportByName(n):null;}catch(e){}
  return (typeof Module.findGlobalExportByName==='function')?Module.findGlobalExportByName(n):null; }
function emit(api,det){ send({tipo:'evento', api:api, path:det||''}); }
var inst=0;
function hookC(mod,name,label){ var p=fx(mod,name); if(p){ Interceptor.attach(p,{onEnter:function(){ emit(label||name); }}); inst++; } }
if (ObjC.available){
  // Keychain
  ['SecItemAdd','SecItemCopyMatching','SecItemUpdate','SecItemDelete'].forEach(function(n){hookC('Security',n);});
  // Cripto
  hookC(null,'CCCrypt','CCCrypt');
  // Transporte / SSL
  try{ var S=ObjC.classes.NSURLSession; Interceptor.attach(S['- dataTaskWithRequest:completionHandler:'].implementation,{onEnter:function(a){ try{emit('NSURLSession.dataTask', new ObjC.Object(a[2]).URL().absoluteString().toString());}catch(e){emit('NSURLSession.dataTask');} }}); inst++; }catch(e){}
  // Storage local
  try{ var D=ObjC.classes.NSData; Interceptor.attach(D['- writeToFile:atomically:'].implementation,{onEnter:function(a){ try{emit('NSData.writeToFile', new ObjC.Object(a[2]).toString());}catch(e){emit('NSData.writeToFile');} }}); inst++; }catch(e){}
  try{ var UD=ObjC.classes.NSUserDefaults; Interceptor.attach(UD['- setObject:forKey:'].implementation,{onEnter:function(a){ try{emit('NSUserDefaults.setObject', new ObjC.Object(a[3]).toString());}catch(e){emit('NSUserDefaults.setObject');} }}); inst++; }catch(e){}
  send({tipo:'hook_ready', n:inst});
} else { send({tipo:'erro', msg:'ObjC indisponivel'}); }
