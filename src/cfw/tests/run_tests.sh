#!/usr/bin/env bash
# XLPS2-Alpha CFW — host unit tests (HAL-independent core)
# Compiles each test_*.c together with the static core sources and runs it.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."                 # src/cfw
INC="$ROOT/include"
SRC="$ROOT/src"

CORE=(
  "$SRC/common/cfw_config.c"
  "$SRC/hsm/hsm_current_state.c"
  "$SRC/hsm/hsm_engine.c"
  "$SRC/hsm/hsm_states.c"
  "$SRC/svc/event_bus.c"
  "$SRC/svc/ringbuf.c"
  "$SRC/svc/filter.c"
  "$SRC/svc/kinematics.c"
  "$SRC/svc/param.c"
  "$SRC/svc/diag.c"
  "$SRC/comm/faults/fault_tolerance.c"
)

TOTAL_FAIL=0
for t in "$HERE"/test_*.c; do
  [ -e "$t" ] || continue
  name="$(basename "$t" .c)"
  exe="/tmp/cfw_${name}"
  if ! gcc -std=c11 -Wall -Wextra -I"$INC" "${CORE[@]}" "$t" -o "$exe"; then
    echo "BUILD FAIL: $name"; TOTAL_FAIL=1; continue
  fi
  if ! "$exe"; then TOTAL_FAIL=1; fi
done

if [ "$TOTAL_FAIL" -ne 0 ]; then
  echo "==== HOST TESTS FAILED ===="
  exit 1
fi
echo "==== ALL HOST TESTS PASSED ===="
exit 0
