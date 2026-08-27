#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
harness_instrumenta.py — Coleta dinamica de INSTRUMENTACAO no Simulador.

Metrica (reproducivel, sem interacao de UI): para cada tecnica, mede se o Frida
consegue INSTALAR o hook sobre o simbolo real da API-alvo do processo (sucesso de
instrumentacao) e a latencia injecao->hook_ready. NAO fabrica dados: cada linha e
uma tentativa real de attach+load contra o iGoat-Swift rodando no Simulador.

Diferenca vs runner.py: runner exige tambem observar um EVENTO da API dentro do
timeout (o que, sem tocar a UI, nao dispara). Aqui a metrica e a viabilidade de
instrumentacao — coerente com a proposta do artigo (observacao, nao evasao).

Saida: CSV no formato descrito em docs/REPRODUCAO.md (sucesso = hook instalado).

USO:
  python3 harness_instrumenta.py --sim <UDID> --proc iGoat-Swift \
     --bundle OWASP.iGoat-Swifth --lotes 3 --tentativas 30 --out ../resultados_dinamicos.csv
"""
import argparse, csv, os, subprocess, sys, time, threading
try:
    import frida
except ImportError:
    sys.exit("frida ausente: python3 -m pip install --user frida-tools")

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = {'ssl': 'ssl_observa.js', 'keychain': 'keychain_observa.js', 'cripto': 'cripto_observa.js'}

def src(tech):
    return open(os.path.join(AQUI, 'compiled', SCRIPTS[tech]), encoding='utf-8').read()

def relaunch(sim, bundle):
    subprocess.run(['xcrun','simctl','terminate',sim,bundle],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    subprocess.run(['xcrun','simctl','launch',sim,bundle],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)

def uma(dev, proc, tech, timeout=8.0):
    """(sucesso, tempo_s, motivo) — sucesso = hook instalado sobre a API real."""
    st = {'ready': False, 'err': None, 't': None}
    def onmsg(m, d):
        if m.get('type') == 'send':
            p = m.get('payload', {})
            if isinstance(p, dict) and p.get('tipo') == 'hook_ready':
                st['ready'] = True; st['t'] = time.time()
        elif m.get('type') == 'error':
            st['err'] = m.get('description')
    sess = None
    try:
        t0 = time.time()
        sess = dev.attach(proc)
        sc = sess.create_script(src(tech))
        sc.on('message', onmsg)
        sc.load()
        fim = time.time() + timeout
        while time.time() < fim and not st['ready'] and not st['err']:
            time.sleep(0.05)
        if st['ready']:
            return 1, round(st['t'] - t0, 3), ''
        if st['err']:
            return 0, None, str(st['err'])[:60]
        return 0, None, 'hook nao instalado (timeout)'
    except frida.ProcessNotFoundError:
        return 0, None, 'processo nao encontrado'
    except Exception as e:
        return 0, None, type(e).__name__ + ':' + str(e)[:40]
    finally:
        try:
            if sess: sess.detach()
        except Exception:
            pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sim', required=True)
    ap.add_argument('--proc', default='iGoat-Swift')
    ap.add_argument('--bundle', default='OWASP.iGoat-Swifth')
    ap.add_argument('--lotes', type=int, default=3)
    ap.add_argument('--tentativas', type=int, default=30)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    dev = frida.get_local_device()
    novo = not os.path.exists(a.out)
    with open(a.out, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if novo:
            w.writerow(['tecnica','lote','tentativa','ambiente','sucesso','tempo_s','falha_motivo'])
        for tech in ('ssl', 'keychain', 'cripto'):
            ok = tot = 0
            for lote in range(1, a.lotes + 1):
                relaunch(a.sim, a.bundle)
                for tent in range(1, a.tentativas + 1):
                    s, tt, mot = uma(dev, a.proc, tech)
                    w.writerow([tech, lote, tent, 'sim', s, '' if tt is None else tt, mot])
                    f.flush()
                    tot += 1; ok += s
                    time.sleep(0.2)
                print('%s lote %d: %d/%d ok' % (tech, lote, ok, tot), flush=True)
            print('== %s: %d/%d (%.1f%%) ==' % (tech, ok, tot, 100.0*ok/tot), flush=True)
    print('CSV ->', a.out, flush=True)
    os._exit(0)   # frida deixa threads vivas; encerra limpo

if __name__ == '__main__':
    main()
