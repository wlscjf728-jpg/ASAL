#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMAX=${TMAX:-/srscl/tools/synopsys/TetraMAX/TetraMAX_StandAlone/txs/Q-2019.12-SP5-5/bin/tmax}
TAG=${RESULT_TAG:?RESULT_TAG is required}
EXCLUDE_DIRECT=${EXCLUDE_DIRECT:-0}
mkdir -p "$ROOT/logs" "$ROOT/results/tmax/$TAG"

run_case() {
  case_name=$1
  if [ -f "$ROOT/results/tmax/$TAG/$case_name/summary.rpt" ]; then
    printf '%s\n' "SKIP_COLLAPSED422 $TAG $case_name existing"
    return 0
  fi
  RTL_ROOT="$ROOT" CASE_NAME="$case_name" RESULT_TAG="$TAG" EXCLUDE_DIRECT="$EXCLUDE_DIRECT" \
    "$TMAX" -shell -tcl < "$ROOT/scripts/tmax/run_collapsed422.tcl" \
    > "$ROOT/logs/tmax_${TAG}_${case_name}.log" 2>&1
  printf '%s\n' "DONE_COLLAPSED422 $TAG $case_name"
}

cases="CASE_IARK CASE_SB CASE_SR CASE_MC CASE_RANDOM_seed01 CASE_RANDOM_seed02 CASE_RANDOM_seed03 CASE_RANDOM_seed04 CASE_RANDOM_seed05 CASE_RANDOM_seed06 CASE_RANDOM_seed07 CASE_RANDOM_seed08 CASE_RANDOM_seed09 CASE_RANDOM_seed10 CASE_AUTO_TOPOLOGY"
set -- $cases
active=""
count=0
while [ "$#" -gt 0 ]; do
  case_name=$1
  shift
  run_case "$case_name" &
  active="$active $!"
  count=$((count + 1))
  if [ "$count" -eq 4 ] || [ "$#" -eq 0 ]; then
    for pid in $active; do wait "$pid"; done
    active=""
    count=0
  fi
done
touch "$ROOT/results/${TAG}_COMPLETE"
printf '%s\n' "${TAG}_COMPLETE"
