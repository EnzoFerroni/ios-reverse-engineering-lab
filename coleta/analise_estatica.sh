#!/usr/bin/env bash
# analise_estatica.sh — Indicadores estaticos (T2) por binario iOS.
# Extrai o Mach-O de cada .ipa e usa radare2 para contar, de forma reprodutivel:
#   - funcoes analisadas       (afl)
#   - strings sensiveis        (izz filtrado por termos de seguranca)
#   - pontos de hook candidatos(imports/symbols de APIs instrumentaveis)
# Dump dos itens casados vai para coleta/saidas_estaticas/<app>.{strings,hooks}.txt
# para rastreabilidade. NAO fabrica numeros: tudo vem do binario real.
#
# FATIA DE ARQUITETURA (revisao 17/08/2026)
# Tres dos quatro alvos sao binarios universais (gordos) com as fatias na ordem
# armv7 (1a) e arm64 (2a) — ver coleta/evidencias/06_arquitetura.txt. Sem fixar a
# arquitetura, qual fatia o radare2 carrega depende do host: o radare2 6.1.6 em
# macOS arm64 seleciona a fatia que casa com a maquina (arm64), mas essa escolha
# nao e garantida em outro host nem em outra versao. Para tornar a medida
# determinista, a fatia e agora fixada de duas formas redundantes:
#   1) lipo -thin <ARCH> extrai a fatia antes da analise, quando o binario e gordo;
#   2) -a arm -b <BITS> e passado ao r2/rabin2.
# Os filtros (TERMOS, APIS) e a ordem das contagens sao os mesmos de antes — os
# numeros continuam comparaveis com os ja publicados.
#
# Uso:
#   ./analise_estatica.sh <alvo.ipa> [...]          # arm64 (padrao)
#   ARCH=armv7 OUT=saidas_estaticas_armv7 ./analise_estatica.sh <alvo.ipa> [...]
set -u
cd "$(dirname "$0")"
ARCH="${ARCH:-arm64}"
OUT="${OUT:-saidas_estaticas}"; mkdir -p "$OUT"
case "$ARCH" in
  arm64) BITS=64 ;;
  armv7|armv7s) BITS=32 ;;
  *) echo "ARCH invalida: $ARCH (use arm64 ou armv7)" >&2; exit 2 ;;
esac
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# Termos sensiveis (strings) e APIs instrumentaveis (hooks).
TERMOS='password|passwd|secret|token|api[_-]?key|private[_-]?key|jailbreak|cydia|/bin/|/etc/apt|MobileSubstrate|certificate|pinning|SSLPinning|kSecAttr|SecItem|keychain|AES|CCCrypt|http://|https://'
APIS='SecItemAdd|SecItemCopyMatching|SecItemUpdate|SecItemDelete|SecTrustEvaluate|CCCrypt|fileExistsAtPath|dataTaskWithRequest|NSURLSession|SecKeyCreate|kSecAccessControl'

echo "fatia fixada: $ARCH (-a arm -b $BITS)   saida: $OUT/"
printf "%-18s %10s %12s %12s\n" "app" "funcoes" "str_sens" "hooks"
printf "%-18s %10s %12s %12s\n" "------------------" "----------" "------------" "------------"

for IPA in "$@"; do
  [ -f "$IPA" ] || { echo "ausente: $IPA" >&2; continue; }
  APP=$(basename "$IPA" .ipa)
  rm -rf "$TMP/x"; mkdir -p "$TMP/x"
  unzip -qq -o "$IPA" -d "$TMP/x" 2>/dev/null
  APPDIR=$(find "$TMP/x/Payload" -maxdepth 1 -name "*.app" 2>/dev/null | head -1)
  [ -n "$APPDIR" ] || { echo "sem .app em $IPA" >&2; continue; }
  EXE=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$APPDIR/Info.plist" 2>/dev/null)
  BIN="$APPDIR/$EXE"
  [ -f "$BIN" ] || { echo "sem binario em $IPA" >&2; continue; }

  # Fixa a fatia: extrai com lipo se o binario for gordo, segue direto se for thin.
  # 'lipo -archs' lista as arquiteturas separadas por espaco, sem a ambiguidade de
  # 'lipo -info' (cuja saida "Non-fat file:" contem a substring "fat file").
  ARCHS=$(lipo -archs "$BIN" 2>/dev/null)
  NARCH=$(echo "$ARCHS" | wc -w | tr -d ' ')
  echo "$ARCHS" | grep -qw "$ARCH" || { echo "sem fatia $ARCH em $APP — pulando" >&2; continue; }
  if [ "$NARCH" -gt 1 ]; then
    lipo -thin "$ARCH" "$BIN" -output "$TMP/slice" 2>/dev/null || {
      echo "falha ao extrair $ARCH de $APP — pulando" >&2; continue; }
    BIN="$TMP/slice"
  fi

  # Strings sensiveis (case-insensitive), unicas.
  r2 -a arm -b "$BITS" -q -e bin.cache=true -c 'izzq~...' "$BIN" 2>/dev/null >/dev/null
  rabin2 -a arm -b "$BITS" -zzq "$BIN" 2>/dev/null | grep -aiE "$TERMOS" | sort -u > "$OUT/$APP.strings.txt"
  NSTR=$(wc -l < "$OUT/$APP.strings.txt" | tr -d ' ')

  # Funcoes analisadas.
  NFUN=$(r2 -a arm -b "$BITS" -q -c 'aa;afl' "$BIN" 2>/dev/null | wc -l | tr -d ' ')

  # Pontos de hook: imports/symbols de APIs instrumentaveis.
  { rabin2 -a arm -b "$BITS" -iq "$BIN" 2>/dev/null; rabin2 -a arm -b "$BITS" -sq "$BIN" 2>/dev/null; } \
      | grep -aoiE "$APIS" | sort | uniq -c | sort -rn > "$OUT/$APP.hooks.txt"
  NHOOK=$(awk '{s+=$1} END{print s+0}' "$OUT/$APP.hooks.txt")

  printf "%-18s %10s %12s %12s\n" "$APP" "$NFUN" "$NSTR" "$NHOOK"
done
echo
echo "Dumps por app em $OUT/  (.strings.txt e .hooks.txt)"
