#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMAX=${TMAX_BIN:-tmax}
MAX_JOBS=${MAX_JOBS:-2}
CAPTURE_CYCLES=${CAPTURE_CYCLES:-4}
ABORT_LIMIT=${ABORT_LIMIT:-1000}
OUTPUT_ROOT=${OUTPUT_ROOT:-multicapture4_abort1000}
FAULT_MODE=${FAULT_MODE:-stuck}
if [ -z "${FAULT_SOURCE+x}" ]; then
  case "$FAULT_MODE" in
    transition) FAULT_SOURCE="$ROOT/config/aes_internal_v2_raw_transition.list" ;;
    *) FAULT_SOURCE="$ROOT/config/aes_internal_v2_raw_stuck.list" ;;
  esac
fi

mkdir -p "$ROOT/logs/aes_internal_v2/tmax/$OUTPUT_ROOT/$FAULT_MODE" \
  "$ROOT/results/tmax/aes_internal_v2/$OUTPUT_ROOT/$FAULT_MODE"

while [ ! -f "$ROOT/results/aes_internal_v2_DFT_COMPLETE" ]; do
  printf '%s\n' "WAIT_MULTICAPTURE4_ABORT1000 $FAULT_MODE DFT_NOT_COMPLETE"
  sleep 60
done

run_case() {
  case_name=$1
  summary="$ROOT/results/tmax/aes_internal_v2/$OUTPUT_ROOT/$FAULT_MODE/$case_name/summary.rpt"
  netlist="$ROOT/results/dft/aes_internal_v2/$case_name/${case_name}_post_dft.v"
  if [ ! -f "$netlist" ]; then
    printf '%s\n' "SKIP_MULTICAPTURE4_ABORT1000 $FAULT_MODE $case_name missing_dft_netlist"
    return 0
  fi
  if [ -f "$summary" ] && [ "${TMAX_FORCE:-0}" -ne 1 ]; then
    printf '%s\n' "SKIP_MULTICAPTURE4_ABORT1000 $FAULT_MODE $case_name existing"
    return 0
  fi
  CASE_NAME="$case_name" FAULT_MODE="$FAULT_MODE" FAULT_SOURCE="$FAULT_SOURCE" \
    OUTPUT_ROOT="$OUTPUT_ROOT" CAPTURE_CYCLES="$CAPTURE_CYCLES" \
    ABORT_LIMIT="$ABORT_LIMIT" RTL_ROOT="$ROOT" \
    "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/run_aes_internal_v2_multicapture_abort_case.tcl" \
    > "$ROOT/logs/aes_internal_v2/tmax/$OUTPUT_ROOT/$FAULT_MODE/${case_name}.log" 2>&1
  printf '%s\n' "DONE_MULTICAPTURE4_ABORT1000 $FAULT_MODE $case_name"
}

cases="CASE_IARK CASE_SB CASE_SR CASE_MC"
for seed in 01 02 03 04 05 06 07 08 09 10; do
  cases="$cases CASE_RANDOM_STAGE_seed$seed"
done
for count in 000 032 064 096 128; do
  cases="$cases CASE_MIX_MC_$count"
done

pids=""
pending=0
for case_name in $cases; do
  run_case "$case_name" &
  pids="$pids $!"
  pending=$((pending + 1))
  if [ "$pending" -ge "$MAX_JOBS" ]; then
    for pid in $pids; do wait "$pid"; done
    pids=""
    pending=0
  fi
done
for pid in $pids; do wait "$pid"; done

touch "$ROOT/results/aes_internal_v2_TMAX_${OUTPUT_ROOT}_${FAULT_MODE}_COMPLETE"
printf '%s\n' "AES_INTERNAL_V2_TMAX_${OUTPUT_ROOT}_${FAULT_MODE}_COMPLETE"
