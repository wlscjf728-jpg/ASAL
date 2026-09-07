set root $::env(RTL_ROOT)
set mode $::env(FAULT_MODE)
set case $::env(CASE_NAME)
set case_dir [file join $root results dft $case]
set class_lib /srscl/tools/synopsys/design_compiler_202106/syn/S-2021.06-SP4/doc/syn/dft_tutorial/LIB/class.v
read_netlist $class_lib -library
read_netlist [file join $root results dft $case ${case}_post_dft.v]
run_build_model mor1kx_aes_soc
if {$mode eq "transition"} {
  set_delay -launch_cycle last_shift
  set_faults -model transition
  set_drc [file join $case_dir ${case}.spf]
  set_delay -nopi_changes
  set_delay -nopo_measures
  set_delay -common_launch_capture_clock
  set_delay -allow_multiple_common_clocks
  add_pi_constraints 0 scan_en
  run_drc
  set source [file join $root config transition_faults_all.list]
  set output [file join $root config transition_faults_valid.list]
} else {
  run_drc [file join $case_dir ${case}.spf]
  set_faults -model stuck
  set source [file join $root config canonical_faults_all.list]
  set output [file join $root config stuck_faults_valid.list]
}
read_faults $source
write_faults $output -all -uncollapsed -replace
report_faults -summary > [file join $root reports ${mode}_faults_valid_summary.rpt]
exit
