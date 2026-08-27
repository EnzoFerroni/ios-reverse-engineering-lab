#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
calcular_estatisticas.py
========================
Lê os resultados brutos dos experimentos dinâmicos (CSV) e calcula, por técnica:
  - taxa de sucesso (%) agregada (N=90)
  - desvio padrão entre os lotes (DP, em pontos percentuais)
  - intervalo de confiança de 95% pelo método de Wilson
  - tempo médio de estabilização ± DP (s) e coeficiente de variação (CV, %)

E imprime:
  (1) um resumo legível no terminal;
  (2) as linhas prontas da tabela do artigo (Tabela 3), na ordem das colunas publicadas.

USO:
    python3 calcular_estatisticas.py resultados.csv

FORMATO DO CSV (cabeçalho obrigatório, ver docs/REPRODUCAO.md §5.3):
    tecnica,lote,tentativa,ambiente,sucesso,tempo_s,falha_motivo
    - tecnica: ssl | jailbreak | keychain | cripto   (códigos livres; o mapa abaixo controla o rótulo)
    - lote: 1, 2 ou 3
    - tentativa: 1..30
    - ambiente: sim | device
    - sucesso: 1 (sucesso) ou 0 (falha)
    - tempo_s: tempo de estabilização pós-injeção em segundos (use só nas linhas de sucesso; vazio se falha)
    - falha_motivo: texto livre (opcional)

Sem dependências externas: usa apenas a biblioteca padrão do Python 3.
"""

import csv
import sys
import math
from collections import defaultdict

# Rótulo de cada técnica EXATAMENTE como aparece na tabela do artigo.
ROTULOS = {
    "ssl":       "Validação de transporte (NSURLSession)",
    "keychain":  "Rotinas de Keychain (SecItem*)",
    "cripto":    "Interfaces criptográficas (CCCrypt)",
}
ORDEM = ["ssl", "keychain", "cripto"]


def br(x, casas=1):
    """Formata número com vírgula decimal (pt-BR)."""
    return f"{x:.{casas}f}".replace(".", ",")


def wilson_ic(sucessos, n, z=1.96):
    """Intervalo de confiança de Wilson (95%) para proporção. Retorna (low%, high%)."""
    if n == 0:
        return (0.0, 0.0)
    p = sucessos / n
    denom = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denom
    margem = (z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)) / denom
    return (max(0.0, (centro - margem)) * 100, min(1.0, (centro + margem)) * 100)


def desvio_padrao(valores):
    """Desvio padrão populacional (ddof=0).

    As N=90 tentativas de cada técnica são tratadas como o conjunto completo de
    observações da campanha, e não como amostra de uma população maior. É a mesma
    convenção usada em verificar_numeros.py e nos valores publicados no artigo;
    manter as duas iguais é o que permite a conferência automática bater.
    """
    k = len(valores)
    if k < 2:
        return 0.0
    media = sum(valores) / k
    var = sum((v - media) ** 2 for v in valores) / k
    return math.sqrt(var)


def carregar(caminho):
    linhas = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("tecnica"):
                continue
            r["tecnica"] = r["tecnica"].strip().lower()
            r["lote"] = int(r["lote"])
            r["sucesso"] = int(r["sucesso"])
            r["tempo_s"] = float(r["tempo_s"]) if r.get("tempo_s", "").strip() else None
            linhas.append(r)
    return linhas


def analisar(linhas):
    por_tec = defaultdict(list)
    for r in linhas:
        por_tec[r["tecnica"]].append(r)

    resultados = {}
    for tec, rows in por_tec.items():
        n = len(rows)
        suc = sum(r["sucesso"] for r in rows)
        taxa = 100 * suc / n if n else 0.0

        # DP entre lotes: taxa de sucesso de cada lote, em p.p.
        por_lote = defaultdict(list)
        for r in rows:
            por_lote[r["lote"]].append(r["sucesso"])
        taxas_lote = [100 * sum(v) / len(v) for v in por_lote.values() if v]
        dp_pp = desvio_padrao(taxas_lote)

        low, high = wilson_ic(suc, n)

        # Tempo de estabilização: usa só linhas de sucesso com tempo preenchido
        tempos = [r["tempo_s"] for r in rows if r["sucesso"] == 1 and r["tempo_s"] is not None]
        t_media = sum(tempos) / len(tempos) if tempos else 0.0
        t_dp = desvio_padrao(tempos)
        cv = (100 * t_dp / t_media) if t_media else 0.0

        resultados[tec] = dict(n=n, suc=suc, taxa=taxa, dp_pp=dp_pp,
                               ic=(low, high), lotes=len(taxas_lote),
                               t_media=t_media, t_dp=t_dp, cv=cv)
    return resultados


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    linhas = carregar(sys.argv[1])
    if not linhas:
        print("Nenhum dado encontrado. Verifique o CSV (apague as linhas de exemplo).")
        sys.exit(1)
    res = analisar(linhas)

    print("\n==================== RESUMO ====================")
    for tec in ORDEM + [t for t in res if t not in ORDEM]:
        if tec not in res:
            continue
        d = res[tec]
        rot = ROTULOS.get(tec, tec)
        print(f"\n[{tec}] {rot}")
        print(f"  N={d['n']}  ({d['lotes']} lotes)  sucessos={d['suc']}")
        print(f"  Taxa de sucesso : {br(d['taxa'])}%")
        print(f"  DP entre lotes  : {br(d['dp_pp'])} p.p.")
        print(f"  IC 95% (Wilson) : [{br(d['ic'][0])}; {br(d['ic'][1])}]")
        print(f"  Tempo médio     : {br(d['t_media'], 3)} ± {br(d['t_dp'], 3)} s  "
              f"(CV={br(d['cv'])}%)")
        if d['n'] != 90:
            print(f"  ATENÇÃO: N={d['n']} (esperado 90 = 3 lotes x 30).")

    print("\n============ LINHAS DA TABELA 3 DO ARTIGO ============")
    print("Cenário | Sucesso (%) | DP (p.p.) | IC 95% (Wilson) | Tempo médio ± DP (s) | CV (%)")
    for tec in ORDEM:
        if tec not in res:
            continue
        d = res[tec]
        rot = ROTULOS.get(tec, tec)
        ic = f"[{br(d['ic'][0])}; {br(d['ic'][1])}]"
        print(f"{rot} | {br(d['taxa'])} | {br(d['dp_pp'])} | {ic} | "
              f"{br(d['t_media'], 3)} ± {br(d['t_dp'], 3)} | {br(d['cv'])}")
    print("\nPara conferir se o artigo publicado bate com estes valores:")
    print("    python3 coleta/verificar_numeros.py\n")


if __name__ == "__main__":
    main()
