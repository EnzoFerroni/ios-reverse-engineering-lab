#!/usr/bin/env bash
# antidebug.sh — conta, de forma reprodutível, os primitivos de resistência à depuração
# em cada binário Mach-O, para sustentar a Tabela 5 do artigo.
#
#   bash coleta/antidebug.sh alvos/DVIA-v2/DVIA-v2.ipa alvos/iGoat-Swift/iGoat-Swift.ipa
#
# Para cada alvo imprime, por primitivo, três contagens obtidas por caminhos diferentes:
#   imports   símbolos importados (rabin2 -i)   — a chamada existe e vem de fora
#   simbolos  tabela de símbolos (rabin2 -s)    — inclui símbolos locais
#   strings   sequências no binário (rabin2 -zz)— constantes e nomes soltos
#
# As três colunas raramente coincidem, e é justamente essa diferença que revela a
# natureza de cada ocorrência. Um primitivo realmente usado como defesa costuma
# aparecer em imports; um nome que só aparece em strings pode ser de outra origem,
# como uma biblioteca de relatório de falhas.
set -u
command -v rabin2 >/dev/null || { echo "rabin2 nao encontrado (brew install radare2)"; exit 1; }

PRIMITIVOS='ptrace|PT_DENY_ATTACH|sysctl|P_TRACED|kinfo_proc|KERN_PROC|task_get_exception_ports|isDebuggerAttached'
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

for IPA in "$@"; do
  [ -f "$IPA" ] || { echo "ausente: $IPA" >&2; continue; }
  APP=$(basename "$IPA" .ipa)
  rm -rf "$TMP/x"; mkdir -p "$TMP/x"
  unzip -qq -o "$IPA" -d "$TMP/x" 2>/dev/null
  APPDIR=$(find "$TMP/x/Payload" -maxdepth 1 -name '*.app' 2>/dev/null | head -1)
  EXE=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$APPDIR/Info.plist" 2>/dev/null)
  BIN="$APPDIR/$EXE"
  [ -f "$BIN" ] || { echo "sem binario em $IPA" >&2; continue; }

  echo "=============================================================="
  echo "ALVO: $APP   ($EXE)"
  echo "=============================================================="
  printf "%-28s %8s %9s %9s\n" "primitivo" "imports" "simbolos" "strings"
  printf "%-28s %8s %9s %9s\n" "----------------------------" "--------" "---------" "---------"

  IMP=$(rabin2 -iq "$BIN" 2>/dev/null)
  SYM=$(rabin2 -sq "$BIN" 2>/dev/null)
  STR=$(rabin2 -zzq "$BIN" 2>/dev/null)

  echo "$PRIMITIVOS" | tr '|' '\n' | while read -r P; do
    A=$(printf '%s\n' "$IMP" | grep -ci "$P")
    B=$(printf '%s\n' "$SYM" | grep -ci "$P")
    C=$(printf '%s\n' "$STR" | grep -ci "$P")
    printf "%-28s %8s %9s %9s\n" "$P" "$A" "$B" "$C"
  done

  echo
  echo "-- de onde vem cada ocorrencia de sysctl (para conferir a origem) --"
  printf '%s\n' "$SYM" | grep -i sysctl | head -12
  echo
done
echo "Cole esta saida na conversa para que a Tabela 5 seja corrigida com base nela."
