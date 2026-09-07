set root $::env(RTL_ROOT)
set case $::env(CASE_NAME)
set tag $::env(RESULT_TAG)
set exclude_direct $::env(EXCLUDE_DIRECT)
set case_dir [file join $root results tmax $tag $case]
file mkdir $case_dir

set class_lib /srscl/tools/synopsys/design_compiler_202106/syn/S-2021.06-SP4/doc/syn/dft_tutorial/LIB/class.v
read_netlist $class_lib -library
read_netlist [file join $root results dft $case ${case}_post_dft.v]
run_build_model mor1kx_aes_soc
set_drc [file join $root results dft $case ${case}.spf]
run_drc
set_faults -model stuck
read_faults [file join $root config historical_canonical_faults_422.list]
if {$exclude_direct eq "1"} {
  read_faults [file join $root config direct_variable_faults.list] -delete
}
set_atpg -abort 100 -num_processes 2
run_atpg -auto
report_summaries > [file join $case_dir summary.rpt]
report_faults -summary > [file join $case_dir faults_summary.rpt]
redirect -file [file join $case_dir detailed_faults_uncollapsed.rpt] {
  report_faults -all -uncollapsed -verbose
}
exit
