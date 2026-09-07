#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMAX=${TMAX_BIN:-/srscl/tools/synopsys/TetraMAX/TetraMAX_StandAlone/txs/Q-2019.12-SP5-5/bin/tmax}
MODE=${FAULT_MODE:-stuck}

mkdir -p "$ROOT/logs/aes_internal_v2/tmax/balanced4/$MODE" "$ROOT/results/tmax/aes_internal_v2/balanced4/$MODE"
while [ ! -f "$ROOT/results/aes_internal_v2_DFT_COMPLETE" ]; do
  printf '%s\n' "WAIT_BALANCED_TMAX_V2 $MODE DFT_NOT_COMPLETE"
  sleep 60
done

run_case() {
  case_name=$1
  source="$ROOT/config/aes_internal_v2_balanced4_${MODE}.list"
  summary="$ROOT/results/tmax/aes_internal_v2/balanced4/$MODE/$case_name/summary.rpt"
  netlist="$ROOT/results/dft/aes_internal_v2/$case_name/${case_name}_post_dft.v"
  if [ ! -f "$netlist" ]; then
    printf '%s\n' "SKIP_BALANCED_TMAX_V2 $MODE $case_name missing_dft_netlist"
    return 0
  fi
  if [ -f "$summary" ] && [ "${TMAX_FORCE:-0}" -ne 1 ]; then
    printf '%s\n' "SKIP_BALANCED_TMAX_V2 $MODE $case_name existing"
    return 0
  fi
  CASE_NAME="$case_name" FAULT_MODE="$MODE" BALANCED_SOURCE="$source" RTL_ROOT="$ROOT" \
    "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/run_aes_internal_v2_balanced_case.tcl" \
    > "$ROOT/logs/aes_internal_v2/tmax/balanced4/$MODE/${case_name}.log" 2>&1
  printf '%s\n' "DONE_BALANCED_TMAX_V2 $MODE $case_name"
}

cases="CASE_IARK CASE_SB CASE_SR CASE_MC"
for seed in 01 02 03 04 05 06 07 08 09 10; do cases="$cases CASE_RANDOM_STAGE_seed$seed"; done
for count in 000 032 064 096 128; do cases="$cases CASE_MIX_MC_$count"; done
cases="$cases CASE_AUTO_STAGE"

pending=0
for case_name in $cases; do
  run_case "$case_name" &
  pid=$!
  if [ "$pending" -eq 0 ]; then
    p1=$pid
    pending=1
  else
    p2=$pid
    wait "$p1"
    wait "$p2"
    pending=0
  fi
done
if [ "$pending" -eq 1 ]; then
  wait "$p1"
fi
touch "$ROOT/results/aes_internal_v2_TMAX_BALANCED4_${MODE}_COMPLETE"
printf '%s\n' "AES_INTERNAL_V2_TMAX_BALANCED4_${MODE}_COMPLETE"
