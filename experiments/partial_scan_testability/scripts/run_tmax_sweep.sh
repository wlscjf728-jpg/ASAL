#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMAX=${TMAX:-tmax}
MODE=${FAULT_MODE:-stuck}
mkdir -p "$ROOT/logs" "$ROOT/results/tmax/$MODE"

run_case() {
  case_name=$1
  if [ -f "$ROOT/results/tmax/$MODE/$case_name/summary.rpt" ]; then
    printf '%s\n' "SKIP_TMAX $MODE $case_name existing"
    return 0
  fi
  RTL_ROOT="$ROOT" CASE_NAME="$case_name" FAULT_MODE="$MODE" \
    "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/run_case.tcl" \
    > "$ROOT/logs/tmax_${MODE}_${case_name}.log" 2>&1
  printf '%s\n' "DONE_TMAX $MODE $case_name"
}

if [ "$MODE" = "transition" ] && [ ! -f "$ROOT/config/transition_faults_all.list" ]; then
  RTL_ROOT="$ROOT" "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/build_transition_faults.tcl" \
    > "$ROOT/logs/tmax_build_transition_faults.log" 2>&1
fi

cases="CASE_IARK CASE_SB CASE_SR CASE_MC CASE_RANDOM_seed01 CASE_RANDOM_seed02 CASE_RANDOM_seed03 CASE_RANDOM_seed04 CASE_RANDOM_seed05 CASE_RANDOM_seed06 CASE_RANDOM_seed07 CASE_RANDOM_seed08 CASE_RANDOM_seed09 CASE_RANDOM_seed10 CASE_AUTO_TOPOLOGY"
set -- $cases
while [ "$#" -gt 0 ]; do
  first=$1; shift
  if [ "$#" -gt 0 ]; then
    second=$1; shift
    run_case "$first" & p1=$!
    run_case "$second" & p2=$!
    wait "$p1"; wait "$p2"
  else
    run_case "$first"
  fi
done
touch "$ROOT/results/TMAX_${MODE}_SWEEP_COMPLETE"
printf '%s\n' "TMAX_${MODE}_SWEEP_COMPLETE"
