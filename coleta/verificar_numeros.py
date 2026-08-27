#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_numeros.py — confere se os números publicados no artigo batem com os dados brutos.

O script NÃO confia em nenhum valor digitado: ele recalcula tudo a partir dos CSVs de
coleta/ e depois lê as tabelas do artigo entregue (.docx) para comparar célula a célula.
Qualquer divergência faz o script terminar com código de saída 1.

    python3 coleta/verificar_numeros.py

Sem dependências externas: apenas a biblioteca padrão do Python 3.
"""

import csv
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIN = os.path.join(RAIZ, 'coleta', 'resultados_dinamicos.csv')
CSV_EST = os.path.join(RAIZ, 'coleta', 'resultados_estaticos.csv')
DOCX = os.path.join(RAIZ, 'artigo', 'Artigo_IC_Enzo_Ferroni_2026.docx')

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
Z = 1.959963985            # z para 95%
falhas = []


# ----------------------------------------------------------------- estatística
def wilson(sucessos, n, z=Z):
    """Intervalo de confiança de Wilson para uma proporção binomial."""
    if n == 0:
        return (0.0, 0.0)
    p = sucessos / n
    denom = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denom
    meia = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centro - meia) * 100, min(1.0, centro + meia) * 100)


def media(xs):
    return sum(xs) / len(xs) if xs else 0.0


def desvio(xs):
    """Desvio padrão populacional."""
    if len(xs) < 2:
        return 0.0
    m = media(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


# ----------------------------------------------------------------- leitura docx
def tabelas_do_docx(caminho):
    """Devolve as tabelas do .docx como listas de listas de texto."""
    with zipfile.ZipFile(caminho) as z:
        raiz = ET.fromstring(z.read('word/document.xml'))
    saida = []
    for tbl in raiz.iter(W + 'tbl'):
        linhas = []
        for tr in tbl.findall(W + 'tr'):
            celulas = []
            for tc in tr.findall(W + 'tc'):
                celulas.append(''.join(t.text or '' for t in tc.iter(W + 't')).strip())
            linhas.append(celulas)
        saida.append(linhas)
    return saida


def num(txt):
    """'0,111 ± 0,033' -> 0.111 ; '19.015' -> 19015 ; devolve None se não houver número."""
    txt = txt.split('±')[0].strip()
    txt = txt.replace('.', '') if re.fullmatch(r'[\d.]+', txt) and ',' not in txt else txt
    txt = txt.replace(',', '.')
    m = re.search(r'-?\d+(?:\.\d+)?', txt)
    return float(m.group(0)) if m else None


def conferir(rotulo, calculado, publicado, tol=0.05):
    ok = publicado is not None and abs(calculado - publicado) <= tol
    print('  %-58s calc=%-10s artigo=%-10s %s'
          % (rotulo, f'{calculado:g}', f'{publicado:g}' if publicado is not None else '—',
             'OK' if ok else 'DIVERGE'))
    if not ok:
        falhas.append(rotulo)


# ----------------------------------------------------------------- verificações
def main():
    for caminho in (CSV_DIN, CSV_EST, DOCX):
        if not os.path.exists(caminho):
            sys.exit('arquivo ausente: %s' % caminho)

    tabelas = tabelas_do_docx(DOCX)
    print('Artigo: %s' % os.path.relpath(DOCX, RAIZ))
    print('Tabelas encontradas no artigo: %d\n' % len(tabelas))

    # ---------------------------------------------------- 1. dados dinâmicos
    linhas = list(csv.DictReader(open(CSV_DIN, encoding='utf-8')))
    por_tecnica = defaultdict(list)
    for r in linhas:
        por_tecnica[r['tecnica']].append(r)

    # a tabela do artigo cujo cabeçalho tem 'IC 95%'
    t_din = next((t for t in tabelas if any('IC 95' in c for c in t[0])), None)
    if t_din is None:
        sys.exit('não encontrei a tabela de desempenho dinâmico no artigo')

    # mapeia o código da técnica para a linha correspondente da tabela publicada
    chave = {'ssl': 'transporte', 'keychain': 'keychain', 'cripto': 'criptográficas'}
    print('[1] Instrumentação dinâmica — recalculado de %s'
          % os.path.relpath(CSV_DIN, RAIZ))

    for tecnica in ('ssl', 'keychain', 'cripto'):
        regs = por_tecnica[tecnica]
        n = len(regs)
        sucessos = sum(int(r['sucesso']) for r in regs)
        taxa = 100.0 * sucessos / n
        tempos = [float(r['tempo_s']) for r in regs if r['tempo_s']]
        m, dp = media(tempos), desvio(tempos)
        cv = 100.0 * dp / m if m else 0.0
        lo, hi = wilson(sucessos, n)

        # taxas por lote -> DP entre lotes, em pontos percentuais
        lotes = defaultdict(list)
        for r in regs:
            lotes[r['lote']].append(int(r['sucesso']))
        taxas_lote = [100.0 * sum(v) / len(v) for v in lotes.values()]
        dp_lotes = desvio(taxas_lote)

        alvo = next((ln for ln in t_din[1:]
                     if chave[tecnica].lower() in ln[0].lower()), None)
        if alvo is None:
            falhas.append('linha da técnica %s ausente no artigo' % tecnica)
            print('  %-58s AUSENTE NO ARTIGO' % tecnica)
            continue

        print('  técnica "%s"  (N=%d, %d lotes)' % (tecnica, n, len(lotes)))
        conferir('    taxa de sucesso (%)', taxa, num(alvo[1]), tol=0.05)
        conferir('    DP entre lotes (p.p.)', dp_lotes, num(alvo[2]), tol=0.05)
        conferir('    IC 95% inferior (Wilson)', lo, num(alvo[3]), tol=0.05)
        conferir('    tempo médio (s)', m, num(alvo[4]), tol=0.0005)
        conferir('    desvio do tempo (s)', dp,
                 num(alvo[4].split('±')[1]) if '±' in alvo[4] else None, tol=0.0005)
        conferir('    coeficiente de variação (%)', cv, num(alvo[5]), tol=0.05)

        if n != 90:
            falhas.append('N esperado de 90 na técnica %s, encontrado %d' % (tecnica, n))

    # técnicas presentes no CSV mas ausentes do artigo (e vice-versa)
    extras = set(por_tecnica) - {'ssl', 'keychain', 'cripto'}
    if extras:
        print('\n  aviso: o CSV tem técnicas não publicadas: %s' % ', '.join(sorted(extras)))

    # ---------------------------------------------------- 2. dados estáticos
    print('\n[2] Indicadores estáticos — recalculado de %s'
          % os.path.relpath(CSV_EST, RAIZ))
    est = {r['alvo']: r for r in csv.DictReader(open(CSV_EST, encoding='utf-8'))}

    t_est = next((t for t in tabelas
                  if any('Funções recuperadas' in c for c in t[0])), None)
    if t_est is None:
        sys.exit('não encontrei a tabela de indicadores estáticos no artigo')

    mapa = {'DVIA-v2': 'DVIA-v2', 'iGoat-Swift': 'iGoat-Swift',
            'UnCrackable-L1+L2': 'UnCrackable'}
    for chave_csv, prefixo in mapa.items():
        reg = est.get(chave_csv)
        if reg is None:
            falhas.append('alvo %s ausente no CSV estático' % chave_csv)
            continue
        alvo = next((ln for ln in t_est[1:] if ln[0].startswith(prefixo)), None)
        if alvo is None:
            falhas.append('alvo %s ausente na tabela do artigo' % prefixo)
            continue
        print('  alvo "%s"' % chave_csv)
        conferir('    funções recuperadas', float(reg['funcoes_recuperadas']),
                 num(alvo[1]), tol=0.5)
        conferir('    cadeias sensíveis', float(reg['strings_sensiveis']),
                 num(alvo[2]), tol=0.5)
        conferir('    símbolos instrumentáveis', float(reg['simbolos_instrumentaveis']),
                 num(alvo[3]), tol=0.5)

    # coerência interna: a soma da tabela de criticidade tem de bater com a estática
    soma_estatica = sum(int(est[k]['simbolos_instrumentaveis']) for k in mapa)
    t_crit = next((t for t in tabelas
                   if any('Família de interface' in c for c in t[0])), None)
    if t_crit:
        soma_crit = sum(num(ln[1]) or 0 for ln in t_crit[1:])
        print('\n[3] Coerência interna entre tabelas')
        conferir('    soma dos símbolos por família = total da estática',
                 soma_estatica, soma_crit, tol=0.5)

    # ---------------------------------------------------- 3. números soltos no texto
    print('\n[4] Afirmações numéricas do texto corrido')
    with zipfile.ZipFile(DOCX) as z:
        raiz = ET.fromstring(z.read('word/document.xml'))
    texto = ''.join(t.text or '' for t in raiz.iter(W + 't'))

    total_tentativas = len(linhas)
    if 'noventa tentativas por cenário' in texto and len(por_tecnica['ssl']) != 90:
        falhas.append('o texto afirma N=90 por cenário, mas o CSV discorda')
    print('  %-58s %s' % ('total de tentativas registradas no CSV', total_tentativas))
    print('  %-58s %s' % ('N por cenário afirmado no texto (90)',
                          'OK' if len(por_tecnica['ssl']) == 90 else 'DIVERGE'))

    # convenção de terminologia do projeto: a medida é observabilidade, não
    # evasão; e o ponto de entrada no iOS é Objective-C, não a ponte Java/Android
    vetados = ['bypass', 'Java.perform']
    reaparecidos = [p for p in vetados if p.lower() in texto.lower()]
    print('  %-58s %s' % ('convenção de terminologia do artigo',
                          'respeitada' if not reaparecidos
                          else 'VIOLADA: ' + ', '.join(reaparecidos)))
    if reaparecidos:
        falhas.extend('reapareceu no texto: %s' % p for p in reaparecidos)

    # ---------------------------------------------------- 5. numeracao de elementos
    print('\n[5] Numeração e chamadas de figuras, tabelas e quadros')
    paras = [''.join(t.text or '' for t in par.iter(W + 't'))
             for par in raiz.iter(W + 'p')]
    for especie in ('Figura', 'Tabela', 'Quadro'):
        # legendas: parágrafo que COMEÇA com "Especie N."
        legendas = sorted(int(m.group(1)) for p_ in paras
                          for m in [re.match(especie + r' (\d+)\.', p_.strip())] if m)
        # chamadas no corpo: "Especie N" fora das legendas
        citados = set(int(n) for n in re.findall(especie + r's? (\d+)', texto))
        citados |= set(int(n) for n in re.findall(especie + r's \d+ e (\d+)', texto))
        esperado = list(range(1, len(legendas) + 1))
        ok_seq = legendas == esperado
        nao_citados = [n for n in legendas if n not in citados]
        orfas = [n for n in citados if n not in legendas]
        print('  %-8s %d elemento(s): %s' % (especie, len(legendas),
              ', '.join(map(str, legendas)) or '—'))
        if not ok_seq:
            falhas.append('%s: numeração com lacuna ou repetição (esperado %s)'
                          % (especie, esperado))
            print('    numeração fora de sequência — esperado %s' % esperado)
        if nao_citados:
            falhas.append('%s sem chamada no texto: %s' % (especie, nao_citados))
            print('    sem chamada no texto: %s' % nao_citados)
        if orfas:
            falhas.append('%s citada mas inexistente: %s' % (especie, orfas))
            print('    citada no texto mas inexistente: %s' % orfas)
        if ok_seq and not nao_citados and not orfas:
            print('    sequência completa e todas citadas — OK')

    # ---------------------------------------------------- resultado
    print('\n' + '-' * 78)
    if falhas:
        print('FALHOU — %d divergência(s):' % len(falhas))
        for f in falhas:
            print('  - %s' % f)
        return 1
    print('OK — todos os números publicados batem com os dados brutos.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
