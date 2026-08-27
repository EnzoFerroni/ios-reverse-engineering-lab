# Como reproduzir os experimentos

Este guia permite refazer, do zero, a coleta que sustenta os números do artigo
`artigo/Artigo_IC_Enzo_Ferroni_2026.pdf`.

Se você só quer **conferir** os resultados, sem refazer nada, comece pela seção 1.

---

## 1. Conferir os números publicados (2 minutos, sem instalar nada)

```bash
git clone https://github.com/EnzoFerroni/ios-reverse-engineering-lab.git
cd ios-reverse-engineering-lab
python3 coleta/verificar_numeros.py
```

O script recalcula, a partir dos CSVs brutos, todos os números publicados — taxa de
sucesso, desvio padrão entre lotes, intervalo de confiança de Wilson, tempo médio,
coeficiente de variação e os indicadores estáticos — e compara célula a célula com as
tabelas lidas do próprio artigo. Termina com código 0 se tudo bate e 1 se algo diverge.
Usa apenas a biblioteca padrão do Python 3.

Ele também confere a coerência interna entre tabelas (a soma dos símbolos por família de
interface tem de igualar o total da análise estática) e a numeração de figuras, tabelas e
quadros.

---

## 2. Ambiente

Os resultados publicados foram obtidos neste ambiente:

| Componente | Versão | Papel |
|---|---|---|
| macOS em Apple Silicon (M4) | ARM64 | estação única de análise |
| Xcode | 26.5 | compilação dos alvos e Simulador iOS |
| Ghidra | via Homebrew | desmontagem e grafo de fluxo de controle |
| radare2 / rabin2 | 6.1.x | indicadores estáticos automáticos |
| Frida (Python) | **17.12.0 — fixar** | instrumentação dinâmica |
| frida-compile + frida-objc-bridge | via npm | empacotamento dos scripts |
| Objection | atual | exploração interativa do runtime |
| Node / npm | 24 / 11 | apenas para o frida-compile |

```bash
python3 -m pip install --user --break-system-packages "frida==17.12.0" frida-tools objection
brew install radare2
cd coleta/frida && npm install
```

### Armadilhas conhecidas

- **Não use Frida 16.** Ele não anexa ao Simulador (`module not found at
  /usr/lib/libSystem.B.dylib`).
- **Frida 17 removeu o global `ObjC` e `Module.findExportByName`.** Por isso os scripts
  usam `frida-objc-bridge`, que precisa ser empacotado com `frida-compile` (seção 5.2).
  Rodar os `.js` da raiz de `coleta/frida/` diretamente não funciona.
- `pip` direto quebra neste ambiente; use `python3 -m pip ... --break-system-packages`.
- O Frida não entra no `PATH` por padrão:
  `export PATH="$HOME/Library/Python/3.14/bin:$PATH"`.

---

## 3. Obter os alvos

Os binários **não são versionados**: são código de terceiros e arquivos grandes.

```bash
mkdir -p alvos && cd alvos
git clone --depth 1 https://github.com/prateek147/DVIA-v2.git
git clone --depth 1 https://github.com/OWASP/iGoat-Swift.git
git clone --depth 1 https://github.com/OWASP/owasp-mastg.git   # UnCrackable L1 e L2
```

Duas observações que custaram tempo:

- Os `.ipa` pré-compilados trazem binários **de dispositivo**: servem para a análise
  estática, mas **não instalam no Simulador**.
- ⚠️ **Três dos quatro alvos são binários universais (gordos)**, e a ordem das fatias é
  `armv7` primeiro, `arm64` depois: iGoat-Swift, UnCrackable-Level1 e UnCrackable-Level2.
  Só o DVIA-v2 é *thin* `arm64`. Confira antes de medir qualquer coisa:

  ```bash
  lipo -archs "Payload/<App>.app/<Executável>"
  ```

  **Fixe a fatia sempre.** Qual fatia uma ferramenta carrega quando a arquitetura não é
  indicada depende da ferramenta, da versão e do host — não é determinista. Neste ambiente
  (radare2/rabin2 6.1.6, host macOS ARM64) o radare2 escolheu a fatia `arm64`, que casa com
  a máquina; o Ghidra 11.4.2, no mesmo arquivo, carregou a primeira fatia, `armv7`. O
  `analise_estatica.sh` já fixa a fatia de duas formas redundantes — `lipo -thin` antes da
  análise e `-a arm -b 64` no r2/rabin2 — e aceita `ARCH=armv7` para reproduzir a
  comparação registrada em `coleta/resultados_estaticos_armv7.csv`. Evidência dos
  cabeçalhos: `coleta/evidencias/06_arquitetura.txt`.

  No Ghidra, importe a fatia explicitamente (a caixa *Batch Import* lista as duas) ou
  extraia antes com `lipo -thin arm64`; confira no *disassembly* que aparecem registradores
  `x`/`w` e instruções `stp`/`ldp`/`bl`. Se aparecerem `r0`–`r11` ou `movw`/`movt`, o que
  está carregado é a fatia `armv7`.
- **DVIA-v2 não compila para o Simulador** — o pod Realm usado é antigo e não tem fatia
  arm64-simulator. Para a etapa dinâmica no Simulador, o alvo é o iGoat-Swift.

---

## 4. Etapa estática — Tabela 1 do artigo

```bash
B=$PWD/alvos
bash coleta/analise_estatica.sh \
  "$B/DVIA-v2/DVIA-v2.ipa" \
  "$B/iGoat-Swift/iGoat-Swift.ipa" \
  "$B/owasp-mastg/Crackmes/iOS/Level_01/UnCrackable-Level1.ipa" \
  "$B/owasp-mastg/Crackmes/iOS/Level_02/UnCrackable-Level2.ipa"
```

O script extrai o Mach-O de cada `.ipa` e conta, de forma automática e reprodutível:

- **funções recuperadas** — `r2 -c 'aa;afl'`;
- **cadeias sensíveis** — `rabin2 -zzq` filtrado por uma lista fixa de termos de segurança
  (senhas, chaves, indicadores de ambiente, criptografia, URLs);
- **símbolos instrumentáveis** — `rabin2 -i` e `-s` casados com a lista de interfaces de
  Keychain, validação de transporte e criptografia.

Os itens casados são despejados em `coleta/saidas_estaticas/` (regenerável, não
versionado) para permitir auditoria linha a linha. O consolidado fica em
`coleta/resultados_estaticos.csv`.

Valores esperados: DVIA-v2 19.015/1.288/60 · iGoat-Swift 9.087/298/22 ·
UnCrackable L1+L2 326/44/10.

> As contagens são automáticas, não subconjuntos curados à mão. É isso que permite que
> outra pessoa chegue exatamente aos mesmos números.

---

## 5. Etapa dinâmica — Tabela 3 e Figura 4

### 5.1 Preparar o alvo no Simulador

```bash
cd alvos/iGoat-Swift/iGoat-Swift && pod install
xcodebuild -workspace iGoat-Swift.xcworkspace -scheme iGoat-Swift \
  -sdk iphonesimulator -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO ONLY_ACTIVE_ARCH=NO -derivedDataPath /tmp/igoat_dd build

xcrun simctl boot "iPhone 17 Pro Max" 2>/dev/null; open -a Simulator
xcrun simctl install booted /tmp/igoat_dd/Build/Products/Debug-iphonesimulator/iGoat-Swift.app
xcrun simctl launch booted OWASP.iGoat-Swifth
```

Bundle id: `OWASP.iGoat-Swifth`. Nome do processo para o Frida: `iGoat-Swift`.

### 5.2 Compilar os scripts de instrumentação

```bash
cd coleta/frida
npm install
for s in ssl keychain cripto jailbreak combo; do
  ./node_modules/.bin/frida-compile ${s}_observa.js -o compiled/${s}_observa.js
done
./node_modules/.bin/frida-compile smoke_test.js -o compiled/smoke_test.js
```

Rode o `smoke_test.js` antes da coleta: ele dispara uma chamada real de
`SecItemCopyMatching` e confirma que o hook capturou o evento. Se o smoke test não passar,
a coleta inteira sai inválida.

### 5.3 Rodar a coleta

```bash
python3 coleta/frida/harness_instrumenta.py \
  --sim <UDID-do-simulador> --proc iGoat-Swift --bundle OWASP.iGoat-Swifth \
  --lotes 3 --tentativas 30 --out coleta/resultados_dinamicos.csv
```

São 3 lotes de 30 tentativas por técnica, totalizando **N = 90 por cenário**, em três
técnicas: validação de transporte, Keychain e interfaces criptográficas. O harness
reinicia o aplicativo a cada tentativa, para que as medidas sejam independentes.

**O que exatamente é medido.** Sucesso significa que o Frida conseguiu **instalar o hook
sobre o símbolo real** da interface no processo — ou seja, observabilidade. Não significa
evasão de defesa nem exploração de vulnerabilidade. O tempo registrado é a latência entre
a injeção e o `hook_ready`. Essa distinção é o que torna a métrica interpretável, e está
declarada no artigo.

Formato do CSV produzido:

```
tecnica,lote,tentativa,ambiente,sucesso,tempo_s,falha_motivo
```

`tecnica` ∈ {ssl, keychain, cripto}; `ambiente` ∈ {sim, device}; `sucesso` ∈ {0, 1};
`tempo_s` só é preenchido quando `sucesso = 1`.

### 5.4 Estatística

```bash
python3 coleta/calcular_estatisticas.py coleta/resultados_dinamicos.csv
```

Calcula, por técnica: taxa de sucesso agregada, desvio padrão entre os três lotes em
pontos percentuais, intervalo de confiança de 95% pelo método de Wilson e o coeficiente de
variação do tempo de estabilização.

Wilson foi escolhido em vez da aproximação normal porque, com proporção próxima de 1 e
amostra moderada, o intervalo normal produz limites degenerados. Com 90 sucessos em 90
tentativas, Wilson devolve [95,9%; 100,0%] — preserva a incerteza compatível com o tamanho
da amostra em vez de afirmar certeza absoluta.

Ao final, rode `python3 coleta/verificar_numeros.py` para confirmar que os números
recalculados continuam batendo com os publicados.

---

## 6. O que não é reproduzível hoje, e por quê

**Detecção de comprometimento do sistema (jailbreak detection).** Não há dado quantitativo
publicado sobre isso, e é proposital.

O mecanismo só é representativo em dispositivo físico: no Simulador os artefatos que o
aplicativo procura (`/Applications/Cydia.app`, `/bin/bash`, `/etc/apt`) simplesmente não
existem, então qualquer taxa medida ali mediria o Simulador, não a defesa.

A tentativa de estender a coleta ao dispositivo esbarrou em um bloqueio concreto: o Frida
Gadget aborta na inicialização em iOS 26.5 (`SIGTRAP`, `brk 1337`) porque o sandbox nega a
leitura de `sysctl kern.bootargs`. A alternativa seria um aparelho com privilégio elevado,
fora do escopo autorizado do projeto.

O artigo trata esse mecanismo apenas qualitativamente, a partir da evidência estática, e
declara a limitação. Nenhum valor foi estimado.

### Caminho para retomar em dispositivo físico

Se um aparelho adequado ficar disponível, o procedimento é:

```bash
export PATH="$HOME/Library/Python/3.14/bin:$PATH"
objection patchipa -s alvos/DVIA-v2/DVIA-v2.ipa   # injeta o Gadget e reassina
# se não encontrar identidade: security find-identity -v -p codesigning
# instalar com ios-deploy ou Xcode; depois:
frida-ls-devices                                   # confirmar o device USB
python3 coleta/frida/harness_instrumenta.py --ambiente device ...
```

O alvo recomendado no dispositivo é o **DVIA-v2**, que exercita as quatro técnicas e cujo
`.ipa` já é arm64 de dispositivo. Pré-requisitos: aparelho desbloqueado, Developer Mode
ativo e conta de desenvolvedor válida.

Uma nota de honestidade metodológica: observar a rotina de verificação de ambiente em um
aparelho **sem** jailbreak registra a checagem disparando e retornando "não comprometido".
Isso é observação da defesa — coerente com a métrica do artigo — e não evasão.

---

## 7. Onde está cada coisa

| Caminho | Conteúdo |
|---|---|
| `artigo/` | artigo em PDF e DOCX, termo de anuência e figuras publicadas |
| `coleta/resultados_estaticos.csv` | indicadores da Tabela 1 |
| `coleta/resultados_dinamicos.csv` | 270 tentativas registradas (90 por técnica) |
| `coleta/analise_estatica.sh` | coleta estática com radare2/rabin2 |
| `coleta/frida/` | scripts de instrumentação, harness de coleta e smoke test |
| `coleta/calcular_estatisticas.py` | estatística descritiva e inferencial |
| `coleta/verificar_numeros.py` | verificação artigo × dados brutos |

---

## 8. Limites de uso

Os alvos analisados são aplicativos **de código aberto** da suíte educacional da OWASP,
cuja licença autoriza inspeção. Essa delimitação é o que mantém o trabalho dentro da Lei
9.609/1998 sem conflitar com cláusulas contratuais de softwares comerciais.

Os scripts observam e registram chamadas; não alteram valores de retorno. Reproduzir este
trabalho contra aplicativos de terceiros, sem autorização, sai do escopo ético e jurídico
aqui assumido. Condições de uso em `LICENSE.md`.
