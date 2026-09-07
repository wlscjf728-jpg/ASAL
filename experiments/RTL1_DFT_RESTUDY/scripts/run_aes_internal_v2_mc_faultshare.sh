#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMAX=${TMAX_BIN:-/srscl/tools/synopsys/TetraMAX/TetraMAX_StandAlone/txs/Q-2019.12-SP5-5/bin/tmax}
MODE=${FAULT_MODE:-stuck}
WORKERS=${WORKERS:-32}

mkdir -p "$ROOT/logs/aes_internal_v2/tmax/faultshare/$MODE" "$ROOT/results/tmax/aes_internal_v2/faultshare/$MODE"
while [ ! -f "$ROOT/results/aes_internal_v2_DFT_COMPLETE" ]; do
  printf '%s\n' "WAIT_FAULTSHARE_TMAX_V2 $MODE DFT_NOT_COMPLETE"
  sleep 60
done

run_case() {
  level=$1
  case_name=$2
  source="$ROOT/config/aes_internal_v2_faultshare_${level}_${MODE}.list"
  summary="$ROOT/results/tmax/aes_internal_v2/faultshare/$level/$MODE/$case_name/summary.rpt"
  netlist="$ROOT/results/dft/aes_internal_v2/$case_name/${case_name}_post_dft.v"
  if [ ! -f "$netlist" ]; then
    printf '%s\n' "SKIP_FAULTSHARE_TMAX_V2 $MODE $level $case_name missing_dft_netlist"
    return 0
  fi
  if [ -f "$summary" ] && [ "${TMAX_FORCE:-0}" -ne 1 ]; then
    printf '%s\n' "SKIP_FAULTSHARE_TMAX_V2 $MODE $level $case_name existing"
    return 0
  fi
  mkdir -p "$ROOT/logs/aes_internal_v2/tmax/faultshare/$MODE/$level"
  CASE_NAME="$case_name" FAULT_MODE="$MODE" FAULT_LEVEL="$level" FAULT_SOURCE="$source" RTL_ROOT="$ROOT" \
    "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/run_aes_internal_v2_mc_faultshare_case.tcl" \
    > "$ROOT/logs/aes_internal_v2/tmax/faultshare/$MODE/$level/${case_name}.log" 2>&1
  printf '%s\n' "DONE_FAULTSHARE_TMAX_V2 $MODE $level $case_name"
}

cases="CASE_IARK CASE_SB CASE_SR CASE_MC"
for seed in 01 02 03 04 05 06 07 08 09 10; do cases="$cases CASE_RANDOM_STAGE_seed$seed"; done
pids=""
pending=0
for level in mc0314 mc0800 mc1600 mc2400 mc3200; do
  for case_name in $cases; do
    run_case "$level" "$case_name" &
    pids="$pids $!"
    pending=$((pending + 1))
    if [ "$pending" -ge "$WORKERS" ]; then
      for pid in $pids; do wait "$pid"; done
      pids=""
      pending=0
    fi
  done
done
for pid in $pids; do wait "$pid"; done
touch "$ROOT/results/aes_internal_v2_TMAX_FAULTSHARE_${MODE}_COMPLETE"
printf '%s\n' "AES_INTERNAL_V2_TMAX_FAULTSHARE_${MODE}_COMPLETE"
