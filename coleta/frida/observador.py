#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
observador.py — Coleta dinamica DIRIGIDA POR USUARIO.

Anexa ao app no Simulador/dispositivo, instala o hook de OBSERVACAO da tecnica e
registra TODO evento real disparado pelo app enquanto VOCE navega os exercicios
(ex.: abrir o exercicio de Keychain/Data Storage do iGoat). Cada evento vira uma
linha de CSV com carimbo de tempo e a latencia desde a injecao do hook.

Diferente do runner.py (que faz N tentativas spawn/attach), aqui a fonte dos
eventos e a interacao real com a interface — fiel ao fluxo do app. NAO fabrica
dados: so registra o que o app efetivamente chamou.

USO:
  # 1) build + launch do iGoat no simulador (ver README.md)
  # 2) rode o observador e navegue o app por ~N segundos:
  python3 observador.py --tecnica keychain --alvo iGoat-Swift --ambiente sim \
      --duracao 120 --out ../resultados_dinamicos.csv
"""

import argparse
import csv
import os
import sys
import time

try:
    import frida
except ImportError:
    sys.exit("frida nao instalado: python3 -m pip install --user frida-tools")

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = {
    'ssl': 'ssl_observa.js', 'keychain': 'keychain_observa.js',
    'cripto': 'cripto_observa.js', 'jailbreak': 'jailbreak_observa.js',
}


def carregar(tecnica):
    comp = os.path.join(AQUI, 'compiled', SCRIPTS[tecnica])
    cru = os.path.join(AQUI, SCRIPTS[tecnica])
    with open(comp if os.path.isfile(comp) else cru, encoding='utf-8') as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tecnica', required=True, choices=list(SCRIPTS))
    ap.add_argument('--alvo', required=True, help='nome do processo (ex.: iGoat-Swift)')
    ap.add_argument('--ambiente', required=True, choices=['sim', 'device'])
    ap.add_argument('--duracao', type=float, default=120.0, help='segundos de observacao')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    dev = frida.get_usb_device(timeout=10) if args.ambiente == 'device' else frida.get_local_device()
    ps = [p for p in dev.enumerate_processes() if p.name == args.alvo]
    if not ps:
        sys.exit("processo '%s' nao encontrado. Lance o app primeiro." % args.alvo)
    session = dev.attach(ps[0].pid)

    eventos = []
    t_inject = {'t': None}

    def on_msg(m, data):
        if m.get('type') != 'send':
            if m.get('type') == 'error':
                print("  [script error]", m.get('description'))
            return
        p = m['payload']
        if p.get('tipo') == 'hook_ready':
            t_inject['t'] = time.time()
            print("  hook instalado; navegue o app agora...")
        elif p.get('tipo') == 'evento':
            agora = time.time()
            lat = round(agora - t_inject['t'], 3) if t_inject['t'] else ''
            linha = [args.tecnica, args.ambiente, round(agora, 3), lat,
                     p.get('api', ''), p.get('path', p.get('alg', ''))]
            eventos.append(linha)
            print("  EVENTO:", p.get('api'), p.get('path', p.get('alg', '')))

    script = session.create_script(carregar(args.tecnica))
    script.on('message', on_msg)
    script.load()
    print("Observando por %.0fs (Ctrl+C encerra)..." % args.duracao)
    try:
        time.sleep(args.duracao)
    except KeyboardInterrupt:
        pass
    session.detach()

    novo = not os.path.exists(args.out)
    with open(args.out, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if novo:
            w.writerow(['tecnica', 'ambiente', 'timestamp', 'latencia_s', 'api', 'detalhe'])
        w.writerows(eventos)
    print("\n%d eventos reais registrados -> %s" % (len(eventos), args.out))


if __name__ == '__main__':
    main()
