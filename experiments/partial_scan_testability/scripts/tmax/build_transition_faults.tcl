set root $::env(RTL_ROOT)
set class_lib /srscl/tools/synopsys/design_compiler_202106/syn/S-2021.06-SP4/doc/syn/dft_tutorial/LIB/class.v
read_netlist $class_lib -library
read_netlist [file join $root config seqgen_tmax.v]
read_netlist [file join $root results checkpoint mor1kx_aes_soc_pre_dft.v]
run_build_model mor1kx_aes_soc
run_drc
set_faults -model transition
add_faults -all
write_faults [file join $root config transition_faults_all.list] -all -uncollapsed -replace
report_faults -summary > [file join $root reports transition_faults_summary.rpt]
exit
