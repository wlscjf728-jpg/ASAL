# Insert one scan chain into the standalone MC9 design.
set EXTRA_ROOT [file normalize [file join [file dirname [info script]] ..]]
set PROJECT_ROOT [file normalize [file join $EXTRA_ROOT ..]]
if {![info exists ::env(ASAL_LIBRARY_DB)]} {
  error "Set ASAL_LIBRARY_DB to the licensed technology .db file"
}
set LIBRARY [file normalize $::env(ASAL_LIBRARY_DB)]
set RTL_ROOT [file join $EXTRA_ROOT rtl]
if {![file isdirectory $RTL_ROOT]} {
  set RTL_ROOT [file normalize [file join $EXTRA_ROOT .. .. shared rtl]]
}
set PRESCAN [file join $EXTRA_ROOT netlist extra_exp_prescan.ddc]
set REPORT_DIR [file join $EXTRA_ROOT results evaluator]

set_app_var search_path [list [file join $RTL_ROOT] [file dirname $LIBRARY]]
set_app_var target_library [list $LIBRARY]
set_app_var link_library [list * $LIBRARY]
set_app_var verilogout_no_tri true
set_app_var verilogout_single_bit false

file mkdir [file join $EXTRA_ROOT netlist]
file mkdir $REPORT_DIR
read_ddc $PRESCAN
current_design extra_exp_top
link
source [file join [file dirname [info script]] scan_constraints.tcl]

set_scan_element false [all_registers]
set_attribute $selected dont_touch false
set_scan_element true $selected

set_dft_signal -view existing_dft -type ScanClock -port clk -timing {45 55}
set_dft_signal -view existing_dft -type Reset -port reset_n -active_state 0
set_dft_signal -view spec -type TestMode -port test_mode -active_state 1
set_dft_signal -view spec -type ScanEnable -port scan_en -active_state 1
set_dft_signal -view spec -type ScanDataIn -port scan_in
set_dft_signal -view spec -type ScanDataOut -port scan_out
set_scan_configuration -chain_count 1 -style multiplexed_flip_flop
set_scan_register_type -type {FD1S FD2S FD4S}
create_test_protocol

redirect -file [file join $REPORT_DIR dft_drc_before.rpt] { dft_drc }
set insert_status [insert_dft]
if {$insert_status == 0} {
  error "insert_dft returned failure"
}
redirect -file [file join $REPORT_DIR dft_drc_after.rpt] { dft_drc }
redirect -file [file join $REPORT_DIR scan_configuration.rpt] { report_scan_configuration }
redirect -file [file join $REPORT_DIR scan_path.rpt] { report_scan_path }

write -format verilog -hierarchy -output [file join $EXTRA_ROOT netlist extra_exp_postscan.v]
write -format ddc -hierarchy -output [file join $EXTRA_ROOT netlist extra_exp_postscan.ddc]
write_test_protocol -output [file join $EXTRA_ROOT netlist extra_exp_postscan.spf]
write_sdc [file join $EXTRA_ROOT netlist extra_exp_postscan.sdc]

set inventory [open [file join $REPORT_DIR scan_inventory.rpt] w]
puts $inventory "declared_scan_cell_count=256"
puts $inventory "selected_target=aes_core.MC_REG[9]"
foreach name $selected_names { puts $inventory $name }
close $inventory
exit
