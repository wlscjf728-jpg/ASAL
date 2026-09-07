# TetraMAX execution for the equal-weight four-stage-cone fault universe.
set root $::env(RTL_ROOT)
set case $::env(CASE_NAME)
set mode $::env(FAULT_MODE)
set source $::env(BALANCED_SOURCE)
set case_dir [file join $root results tmax aes_internal_v2 balanced4 $mode $case]
file mkdir $case_dir

set class_lib /srscl/tools/synopsys/design_compiler_202106/syn/S-2021.06-SP4/doc/syn/dft_tutorial/LIB/class.v
read_netlist $class_lib -library
read_netlist [file join $root results dft aes_internal_v2 $case ${case}_post_dft.v]
run_build_model mor1kx_aes_soc

if {$mode eq "transition"} {
  set_delay -launch_cycle last_shift
  set_faults -model transition
  set_drc [file join $root results dft aes_internal_v2 $case ${case}.spf]
  set_delay -nopi_changes
  set_delay -nopo_measures
  set_delay -common_launch_capture_clock
  set_delay -allow_multiple_common_clocks
  add_pi_constraints 0 scan_en
  run_drc
  read_faults $source
} else {
  set_drc [file join $root results dft aes_internal_v2 $case ${case}.spf]
  run_drc
  set_faults -model stuck
  read_faults $source
}

set_atpg -abort 100 -num_processes 2
run_atpg -auto
report_summaries > [file join $case_dir summary.rpt]
report_faults -summary > [file join $case_dir faults_summary.rpt]
exit
