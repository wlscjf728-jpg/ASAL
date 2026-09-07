#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DC=${DC_SHELL:-/srscl/tools/synopsys/design_compiler_202106/syn/S-2021.06-SP4/bin/dc_shell}
mkdir -p "$ROOT/logs" "$ROOT/results/dft" "$ROOT/reports/dft_drc"

run_case() {
  case_name=$1
  manifest=$2
  if [ -f "$ROOT/results/dft/$case_name/${case_name}_post_dft.v" ]; then
    printf '%s\n' "SKIP_DFT $case_name existing"
    return 0
  fi
  CASE_NAME="$case_name" MANIFEST="$manifest" \
    "$DC" -64bit -f "$ROOT/scripts/dc/run_case.tcl" \
    > "$ROOT/logs/dft_${case_name}.log" 2>&1
  printf '%s\n' "DONE_DFT $case_name"
}

run_case "CASE_IARK" "config/iark_scan.list" & p1=$!
run_case "CASE_SB" "config/sb_scan.list" & p2=$!
wait "$p1"; wait "$p2"
run_case "CASE_SR" "config/sr_scan.list" & p1=$!
run_case "CASE_MC" "config/mc_scan.list" & p2=$!
wait "$p1"; wait "$p2"
pending=0
for seed in 01 02 03 04 05 06 07 08 09 10; do
  run_case "CASE_RANDOM_seed${seed}" "config/random_scan_seed${seed}.list" &
  pid=$!
  if [ "$pending" -eq 0 ]; then
    p1=$pid
    pending=1
  else
    p2=$pid
    wait "$p1"; wait "$p2"
    pending=0
  fi
done
if [ "$pending" -eq 1 ]; then wait "$p1"; fi
run_case "CASE_AUTO_TOPOLOGY" "config/auto_topology_scan.list"
touch "$ROOT/results/DFT_SWEEP_COMPLETE"
printf '%s\n' "DFT_SWEEP_COMPLETE"
