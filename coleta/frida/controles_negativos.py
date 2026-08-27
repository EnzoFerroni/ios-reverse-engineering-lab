#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
controles_negativos.py — controles negativos da instrumentacao.

Um instrumento que nunca falha pode estar quebrado. Este script submete o mesmo
harness da coleta (harness_instrumenta.uma) a quatro situacoes em que a falha e
ESPERADA, para demonstrar que ele e capaz de registra-la:

  A. Seletor inexistente  — script identico ao ssl_observa.js, mas com o seletor
                            trocado por '- metodoQueNaoExiste:'. O app esta no ar.
  B. Processo ausente     — app encerrado antes da tentativa.
  C. Timeout impossivel   — timeout de 0,001 s, app no ar, script valido.
  D. Processo errado      — nome de processo que nunca existiu.

Nenhuma logica de medicao e reescrita aqui: 'uma()' e importada do harness de
producao, entao o que falha e exatamente o mesmo codigo que produziu os dados
da Tabela 3.

Saida: um CSV por controle, no mesmo formato da coleta dinamica.

USO:
  python3 controles_negativos.py --sim booted --bundle OWASP.iGoat-Swifth \
      --tentativas 10 --outdir ../evidencias
"""
import argparse, csv, os, subprocess, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import harness_instrumenta as H

# Registra o script do controle A sem tocar no harness de producao.
H.SCRIPTS['ssl_inexistente'] = 'ssl_inexistente_observa.js'

CABECALHO = ['tecnica', 'lote', 'tentativa', 'ambiente', 'sucesso', 'tempo_s', 'falha_motivo']

# (id, descricao, processo, tecnica, timeout_s, app_no_ar)
CONTROLES = [
    ('A', 'seletor inexistente',  'iGoat-Swift',          'ssl_inexistente', 8.0,   True),
    ('B', 'processo ausente',     'iGoat-Swift',          'ssl',             8.0,   False),
    ('C', 'timeout impossivel',   'iGoat-Swift',          'ssl',             0.001, True),
    ('D', 'processo errado',      'ProcessoInexistente',  'ssl',             8.0,   True),
]


def app_no_ar(sim, bundle, ligado):
    if ligado:
        H.relaunch(sim, bundle)
    else:
        subprocess.run(['xcrun', 'simctl', 'terminate', sim, bundle],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sim', default='booted')
    ap.add_argument('--bundle', default='OWASP.iGoat-Swifth')
    ap.add_argument('--tentativas', type=int, default=10)
    ap.add_argument('--outdir', default=os.path.join(AQUI, '..', 'evidencias'))
    a = ap.parse_args()

    dev = H.frida.get_local_device()
    resumo = []

    for cid, desc, proc, tech, timeout, ligado in CONTROLES:
        destino = os.path.join(a.outdir, '04_controle_%s.csv' % cid)
        app_no_ar(a.sim, a.bundle, ligado)
        ok = 0
        motivos = {}
        with open(destino, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(CABECALHO)
            for tent in range(1, a.tentativas + 1):
                s, tt, mot = H.uma(dev, proc, tech, timeout=timeout)
                w.writerow([tech, 1, tent, 'sim', s, '' if tt is None else tt, mot])
                f.flush()
                ok += s
                motivos[mot] = motivos.get(mot, 0) + 1
                time.sleep(0.2)
        resumo.append((cid, desc, ok, a.tentativas, motivos, destino))
        print('controle %s (%s): %d/%d sucesso -> %s'
              % (cid, desc, ok, a.tentativas, destino), flush=True)
        for mot, n in motivos.items():
            print('    %dx %s' % (n, mot or '(sem motivo — sucesso)'), flush=True)

    print('\n=== RESUMO ===', flush=True)
    for cid, desc, ok, tot, motivos, _ in resumo:
        dominante = max(motivos.items(), key=lambda kv: kv[1])[0] if motivos else ''
        print('%s | %-22s | sucesso %d/%d | %s' % (cid, desc, ok, tot, dominante), flush=True)

    os._exit(0)   # frida deixa threads vivas; encerra limpo


if __name__ == '__main__':
    main()
