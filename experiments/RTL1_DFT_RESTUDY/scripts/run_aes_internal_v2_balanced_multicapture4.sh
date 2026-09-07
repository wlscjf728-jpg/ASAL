#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMAX=${TMAX_BIN:-/srscl/tools/synopsys/TetraMAX/TetraMAX_StandAlone/txs/Q-2019.12-SP5-5/bin/tmax}
MODE=${FAULT_MODE:-stuck}
MAX_JOBS=${MAX_JOBS:-2}
CAPTURE_CYCLES=${CAPTURE_CYCLES:-4}

mkdir -p "$ROOT/logs/aes_internal_v2/tmax/balanced_multicapture4/$MODE" \
  "$ROOT/results/tmax/aes_internal_v2/balanced_multicapture4/$MODE"

while [ ! -f "$ROOT/results/aes_internal_v2_DFT_COMPLETE" ]; do
  printf '%s\n' "WAIT_BALANCED_MULTICAPTURE4 $MODE DFT_NOT_COMPLETE"
  sleep 60
done

run_case() {
  case_name=$1
  source="$ROOT/config/aes_internal_v2_balanced4_${MODE}.list"
  summary="$ROOT/results/tmax/aes_internal_v2/balanced_multicapture4/$MODE/$case_name/summary.rpt"
  netlist="$ROOT/results/dft/aes_internal_v2/$case_name/${case_name}_post_dft.v"
  if [ ! -f "$netlist" ]; then
    printf '%s\n' "SKIP_BALANCED_MULTICAPTURE4 $MODE $case_name missing_dft_netlist"
    return 0
  fi
  if [ -f "$summary" ] && [ "${TMAX_FORCE:-0}" -ne 1 ]; then
    printf '%s\n' "SKIP_BALANCED_MULTICAPTURE4 $MODE $case_name existing"
    return 0
  fi
  CASE_NAME="$case_name" FAULT_MODE="$MODE" BALANCED_SOURCE="$source" \
    CAPTURE_CYCLES="$CAPTURE_CYCLES" RTL_ROOT="$ROOT" \
    "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/run_aes_internal_v2_balanced_multicapture_case.tcl" \
    > "$ROOT/logs/aes_internal_v2/tmax/balanced_multicapture4/$MODE/${case_name}.log" 2>&1
  printf '%s\n' "DONE_BALANCED_MULTICAPTURE4 $MODE $case_name"
}

# The comparison target is the MC placement versus the ten independent
# random stage placements. The original low balanced result is retained in
# balanced4/ as a protocol baseline and is not overwritten here.
cases="CASE_MC"
for seed in 01 02 03 04 05 06 07 08 09 10; do
  cases="$cases CASE_RANDOM_STAGE_seed$seed"
done

active=0
p1=
for case_name in $cases; do
  run_case "$case_name" &
  pid=$!
  if [ "$active" -eq 0 ]; then
    p1=$pid
    active=1
  else
    p2=$pid
    wait "$p1"
    wait "$p2"
    active=0
  fi
done
if [ "$active" -eq 1 ]; then
  wait "$p1"
fi

touch "$ROOT/results/aes_internal_v2_TMAX_BALANCED_MULTICAPTURE4_${MODE}_COMPLETE"
printf '%s\n' "AES_INTERNAL_V2_TMAX_BALANCED_MULTICAPTURE4_${MODE}_COMPLETE"
