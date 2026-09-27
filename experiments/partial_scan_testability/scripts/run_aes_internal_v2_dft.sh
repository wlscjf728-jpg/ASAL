#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DC=${DC_SHELL:-dc_shell}
mkdir -p "$ROOT/logs/aes_internal_v2" "$ROOT/results/dft/aes_internal_v2"

run_case() {
  case_name=$1
  manifest=$2
  out="$ROOT/results/dft/aes_internal_v2/$case_name/${case_name}_post_dft.v"
  if [ -f "$out" ]; then
    printf '%s\n' "SKIP_DFT_V2 $case_name existing"
    return 0
  fi
  CASE_NAME="$case_name" MANIFEST="$manifest" \
    "$DC" -64bit -f "$ROOT/scripts/dc/run_aes_internal_v2_case.tcl" \
    > "$ROOT/logs/aes_internal_v2/dft_${case_name}.log" 2>&1
  printf '%s\n' "DONE_DFT_V2 $case_name"
}

run_case CASE_IARK config/iark_scan_v2.list & p1=$!
run_case CASE_SB config/sb_scan_v2.list & p2=$!
wait "$p1"; wait "$p2"
run_case CASE_SR config/sr_scan_v2.list & p1=$!
run_case CASE_MC config/mc_scan_v2.list & p2=$!
wait "$p1"; wait "$p2"

pending=0
for seed in 01 02 03 04 05 06 07 08 09 10; do
  run_case "CASE_RANDOM_STAGE_seed${seed}" "config/random_stage_seed${seed}.list" &
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

pending=0
for count in 000 032 064 096 128; do
  run_case "CASE_MIX_MC_${count}" "config/mix_mc_${count}.list" &
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

run_case CASE_AUTO_STAGE config/auto_stage_scan_v2.list
touch "$ROOT/results/aes_internal_v2_DFT_COMPLETE"
printf '%s\n' "AES_INTERNAL_V2_DFT_COMPLETE"
