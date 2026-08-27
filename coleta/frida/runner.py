#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
runner.py — Harness de coleta dinamica (Frida) para o artigo de IC.

Para cada tecnica, executa N lotes x M tentativas contra um alvo iOS
(Simulador ou dispositivo fisico autorizado), injeta o script de OBSERVACAO
correspondente e registra, por tentativa:
  - sucesso (1/0): o hook foi instalado E observou a API alvo dentro do timeout;
  - tempo_s: tempo de estabilizacao pos-injecao (injecao -> primeiro evento);
  - falha_motivo: quando sucesso=0.

A saida e um CSV no formato descrito em docs/REPRODUCAO.md, pronto para
coleta/calcular_estatisticas.py.

NAO fabrica dados: cada linha vem de uma execucao real. Se o alvo nao puder ser
instrumentado (ex.: jailbreak detection em Simulador, que nao se aplica), a
tentativa e registrada como falha com o motivo, ou a tecnica deve ser pulada.

USO (exemplos):
  # Simulador, app ja em execucao, ataca por nome de processo:
  python3 runner.py --tecnica ssl --alvo "DVIA-v2" --ambiente sim \
      --lotes 3 --tentativas 30 --out ../resultados.csv

  # Dispositivo USB, spawn pelo bundle id:
  python3 runner.py --tecnica jailbreak --alvo com.highaltitudehacks.DVIAswiftv2 \
      --ambiente device --spawn --lotes 3 --tentativas 30 --out ../resultados.csv

Requer: frida (pip install frida-tools). Para Simulador, o app roda como processo
no host; para dispositivo, conecte via USB com o app instalavel/depuravel.
"""

import argparse
import csv
import os
import sys
import time

try:
    import frida
except ImportError:
    sys.exit("frida nao instalado. Rode: python3 -m pip install --user frida-tools")

SCRIPTS = {
    'ssl': 'ssl_observa.js',
    'keychain': 'keychain_observa.js',
    'cripto': 'cripto_observa.js',
    'jailbreak': 'jailbreak_observa.js',
}

AQUI = os.path.dirname(os.path.abspath(__file__))


def get_device(ambiente):
    if ambiente == 'device':
        return frida.get_usb_device(timeout=10)
    # Simulador / processos do host
    return frida.get_local_device()


def carregar_script_src(tecnica):
    # Frida 17 removeu o global ObjC; usa-se o bundle compilado (com o
    # frida-objc-bridge embutido) em compiled/. Cai para o fonte cru se nao
    # existir (ex.: Frida <=16, onde o global ObjC ainda existe).
    compilado = os.path.join(AQUI, 'compiled', SCRIPTS[tecnica])
    cru = os.path.join(AQUI, SCRIPTS[tecnica])
    caminho = compilado if os.path.isfile(compilado) else cru
    with open(caminho, 'r', encoding='utf-8') as f:
        return f.read()


def uma_tentativa(device, alvo, tecnica, spawn, timeout):
    """Retorna (sucesso:bool, tempo_s:float|None, motivo:str)."""
    estado = {'ready': False, 'primeiro_evento_t': None, 'erro': None}

    def on_message(message, data):
        if message.get('type') == 'send':
            p = message.get('payload', {})
            if p.get('tipo') == 'hook_ready':
                estado['ready'] = True
            elif p.get('tipo') == 'evento' and estado['primeiro_evento_t'] is None:
                estado['primeiro_evento_t'] = time.time()
            elif p.get('tipo') == 'erro':
                estado['erro'] = p.get('msg')
        elif message.get('type') == 'error':
            estado['erro'] = message.get('description')

    pid = None
    session = None
    try:
        if spawn:
            pid = device.spawn([alvo])
            session = device.attach(pid)
        else:
            session = device.attach(alvo)  # nome ou pid de processo em execucao

        src = carregar_script_src(tecnica)
        script = session.create_script(src)
        script.on('message', on_message)
        t_inject = time.time()
        script.load()
        if spawn:
            device.resume(pid)

        # Aguarda primeiro evento ate timeout.
        fim = time.time() + timeout
        while time.time() < fim and estado['primeiro_evento_t'] is None:
            time.sleep(0.05)

        if estado['primeiro_evento_t'] is not None:
            return True, round(estado['primeiro_evento_t'] - t_inject, 2), ''
        if estado['erro']:
            return False, None, estado['erro'][:60]
        if not estado['ready']:
            return False, None, 'hook nao instalado (timeout)'
        return False, None, 'sem evento observado no timeout'
    except frida.ProcessNotFoundError:
        return False, None, 'processo alvo nao encontrado'
    except frida.TransportError as e:
        return False, None, 'transporte: ' + str(e)[:40]
    except Exception as e:
        return False, None, type(e).__name__ + ': ' + str(e)[:40]
    finally:
        try:
            if session:
                session.detach()
            if spawn and pid:
                device.kill(pid)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description='Harness de coleta dinamica Frida.')
    ap.add_argument('--tecnica', required=True, choices=list(SCRIPTS))
    ap.add_argument('--alvo', required=True, help='nome do processo, pid ou bundle id (com --spawn)')
    ap.add_argument('--ambiente', required=True, choices=['sim', 'device'])
    ap.add_argument('--lotes', type=int, default=3)
    ap.add_argument('--tentativas', type=int, default=30)
    ap.add_argument('--timeout', type=float, default=15.0, help='s ate considerar falha de observacao')
    ap.add_argument('--spawn', action='store_true', help='spawn do app a cada tentativa (em vez de attach)')
    ap.add_argument('--out', required=True, help='CSV de saida (append)')
    ap.add_argument('--pausa', type=float, default=0.5, help='s entre tentativas')
    args = ap.parse_args()

    device = get_device(args.ambiente)
    print('Dispositivo:', device)

    novo = not os.path.exists(args.out)
    with open(args.out, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if novo:
            w.writerow(['tecnica', 'lote', 'tentativa', 'ambiente', 'sucesso', 'tempo_s', 'falha_motivo'])

        total, ok = 0, 0
        for lote in range(1, args.lotes + 1):
            for tent in range(1, args.tentativas + 1):
                sucesso, tempo_s, motivo = uma_tentativa(
                    device, args.alvo, args.tecnica, args.spawn, args.timeout)
                w.writerow([args.tecnica, lote, tent, args.ambiente,
                            1 if sucesso else 0,
                            '' if tempo_s is None else tempo_s, motivo])
                f.flush()
                total += 1
                ok += 1 if sucesso else 0
                print('  lote %d tent %2d: %s %s' % (
                    lote, tent, 'OK' if sucesso else 'FALHA',
                    ('%.2fs' % tempo_s) if tempo_s is not None else ('(' + motivo + ')')))
                time.sleep(args.pausa)

        print('\n%s: %d/%d sucesso (%.1f%%)' % (args.tecnica, ok, total, 100.0 * ok / total))
    print('CSV ->', args.out, '\nAgora: python3 ../calcular_estatisticas.py', args.out)


if __name__ == '__main__':
    main()
