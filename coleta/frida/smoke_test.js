var __b=require('frida-objc-bridge'); var ObjC=__b.default||__b;
function fx(m,n){ if(typeof Module.findExportByName==='function') return Module.findExportByName(m,n);
  try{var x=Process.getModuleByName(m); return x?x.findExportByName(n):null;}catch(e){}
  return (typeof Module.findGlobalExportByName==='function')?Module.findGlobalExportByName(n):null; }
var capt=0, t0=Date.now(), tcap=null;
var p=fx('Security','SecItemCopyMatching');
Interceptor.attach(p,{ onEnter:function(){ if(tcap===null)tcap=Date.now(); capt++; } });
send({tipo:'ready'});
var f=new NativeFunction(p,'int',['pointer','pointer']);
var q=ObjC.classes.NSDictionary.dictionary();  // dict vazio -> errSecParam, sem crash
var res=f(q, NULL);
send({tipo:'fim', capturas:capt, estab_ms:(tcap?tcap-t0:null), ret:res});
