# Engenharia reversa com aplicativos de código aberto em ambientes experimentais controlados

Pesquisa de Iniciação Científica sobre engenharia reversa aplicada a aplicativos iOS,
conduzida em ambiente experimental controlado com ferramentas exclusivamente de código
aberto.

- **Aluno:** Enzo Ferroni — **Orientador:** Prof. Rodrigo Cardoso Silva
- Universidade Presbiteriana Mackenzie — Faculdade de Computação e Informática
- **PIBIC Mackenzie** — XXII Jornada de Iniciação Científica (2026)

## O artigo

📄 **[`artigo/Artigo_IC_Enzo_Ferroni_2026.pdf`](artigo/Artigo_IC_Enzo_Ferroni_2026.pdf)**

O estudo avalia se é possível auditar aplicativos iOS com rigor metodológico e
conformidade jurídica usando apenas ferramentas abertas. A análise estática, com Ghidra e
Radare2, mapeou funções, cadeias sensíveis e símbolos instrumentáveis em quatro binários
da suíte educacional da OWASP. A etapa dinâmica, com Frida, executou três lotes de trinta
tentativas por técnica e mediu a instalação de interceptadores sobre as interfaces de
validação de transporte, Keychain e criptografia.

Um ponto define a leitura dos resultados: **sucesso significa que o hook foi instalado
sobre o símbolo real da interface — observabilidade, não evasão de defesa.** O trabalho
também separa explicitamente o que é observável no Simulador do que só é representativo em
dispositivo físico, e declara como limitação o que não pôde ser medido.

## Conferir os números do artigo

```bash
python3 coleta/verificar_numeros.py
```

O script recalcula todos os valores publicados a partir dos dados brutos e os compara,
célula a célula, com as tabelas lidas do próprio artigo. Sai com código 1 se algo divergir.
Sem dependências externas — só a biblioteca padrão do Python 3.

Ele confere as taxas de sucesso, o desvio padrão entre lotes, o intervalo de confiança de
Wilson, os tempos, os coeficientes de variação, os indicadores estáticos, a coerência
entre tabelas e a numeração de figuras, tabelas e quadros.

## Dados e scripts

| Caminho | Conteúdo |
|---|---|
| [`coleta/resultados_estaticos.csv`](coleta/resultados_estaticos.csv) | indicadores da análise estática por binário (Tabela 1) |
| [`coleta/resultados_dinamicos.csv`](coleta/resultados_dinamicos.csv) | 270 tentativas registradas, 90 por técnica (Tabela 4 e Figura 4) |
| [`coleta/analise_estatica.sh`](coleta/analise_estatica.sh) | coleta estática com radare2/rabin2 |
| [`coleta/frida/`](coleta/frida/) | scripts de instrumentação, harness de coleta e smoke test |
| [`coleta/calcular_estatisticas.py`](coleta/calcular_estatisticas.py) | média, desvio padrão, IC 95% de Wilson e CV |
| [`coleta/verificar_numeros.py`](coleta/verificar_numeros.py) | verificação artigo × dados brutos |

Todo número publicado tem origem em um destes arquivos. Quando um dado não foi coletado,
o artigo registra a limitação em vez de estimar o valor.

## Reproduzir os experimentos

O passo a passo completo — ambiente e versões, armadilhas conhecidas, obtenção dos alvos,
execução das duas etapas de coleta e tratamento estatístico — está em
**[`docs/REPRODUCAO.md`](docs/REPRODUCAO.md)**.

Os aplicativos-alvo não são versionados aqui: são código de terceiros e binários grandes.
O guia explica como obtê-los.

## Escopo e limites

A etapa quantitativa restringe-se ao Simulador iOS e às três técnicas nele
representativas. A avaliação quantitativa da detecção de comprometimento do sistema exige
dispositivo físico e não foi concluída — o bloqueio técnico está documentado no guia de
reprodução. O artigo trata esse mecanismo apenas de forma qualitativa.

Os experimentos restringem-se a aplicativos de código aberto cuja licença autoriza
inspeção. Os scripts observam e registram chamadas; não alteram valores de retorno.
Condições de uso em [`LICENSE.md`](LICENSE.md).

## Citação

Metadados em [`CITATION.cff`](CITATION.cff).
