# DFT insertion branch from the shared pre-DFT checkpoint.
set script_dir [file normalize [file dirname [info script]]]
source [file join $script_dir ../../config/dc_common.tcl]
set root [file normalize [file join $script_dir ../..]]
set case $::env(CASE_NAME)
set manifest [file normalize [file join $root $::env(MANIFEST)]]
set common_manifest [file normalize [file join $root config stage_common_scan.list]]
set case_dir [file join $root results dft $case]
set report_dir [file join $root reports dft_drc $case]
file mkdir $case_dir
file mkdir $report_dir
read_ddc [file join $root results checkpoint mor1kx_aes_soc_pre_dft.ddc]
current_design mor1kx_aes_soc
link
compile -incremental
create_port -direction in scan_en
create_port -direction in scan_in
create_port -direction out scan_out
set all_sequential [all_registers]
catch {set_dont_touch $all_sequential false}
compile -incremental
set_scan_element false [all_registers]

proc read_manifest {path} {
  set values {}
  set fh [open $path r]
  while {[gets $fh line] >= 0} {
    set line [string trim $line]
    if {$line ne "" && ![string match "#*" $line]} { lappend values $line }
  }
  close $fh
  return $values
}
set common_names [read_manifest $common_manifest]
set variable_names [read_manifest $manifest]
if {[llength $variable_names] != 128 || [llength $common_names] != 896} { exit 4 }
set manifest_names [concat $common_names $variable_names]
if {[llength [lsort -unique $manifest_names]] != 1024} { exit 4 }
set all_cells [get_cells -hierarchical *]
set selected [remove_from_collection $all_cells $all_cells]
foreach_in_collection candidate $all_cells {
  set name [get_object_name $candidate]
  if {[lsearch -exact $manifest_names $name] >= 0} { set selected [add_to_collection $selected $candidate] }
}
if {[sizeof_collection $selected] != 1024} { exit 3 }
set_attribute $selected dont_touch false
compile -incremental
set selected_after [remove_from_collection [get_cells -hierarchical *] [get_cells -hierarchical *]]
foreach name $manifest_names {
  set resolved [get_cells -hierarchical -quiet -exact $name]
  if {[sizeof_collection $resolved] != 1} { exit 3 }
  set selected_after [add_to_collection $selected_after $resolved]
}
set_scan_element true $selected_after
create_port -direction in test_mode
set_dft_signal -view existing_dft -type ScanClock -port clk -timing {45 55}
set_dft_signal -view existing_dft -type Reset -port rst -active_state 1
set_dft_signal -view spec -type TestMode -port test_mode -active_state 1
set_dft_signal -view spec -type ScanEnable -port scan_en -active_state 1
set_dft_signal -view spec -type ScanDataIn -port scan_in
set_dft_signal -view spec -type ScanDataOut -port scan_out
set_scan_configuration -chain_count 1 -style multiplexed_flip_flop
set_scan_register_type -type {FD1S FD2S FD4S}
create_test_protocol
redirect -file [file join $report_dir dft_drc_before.rpt] { dft_drc }
insert_dft
redirect -file [file join $report_dir dft_drc_after.rpt] { dft_drc }
redirect -file [file join $report_dir scan_configuration.rpt] { report_scan_configuration }
redirect -file [file join $report_dir scan_path.rpt] { report_scan_path }
write -format ddc -hierarchy -output [file join $case_dir ${case}_post_dft.ddc]
write -format verilog -hierarchy -output [file join $case_dir ${case}_post_dft.v]
write_test_protocol -output [file join $case_dir ${case}.spf]
write_sdc [file join $case_dir ${case}.sdc]
set out [open [file join $case_dir scan_inventory.rpt] w]
puts $out "case=$case"
puts $out "common_manifest_count=[llength $common_names]"
puts $out "variable_manifest_count=[llength $variable_names]"
puts $out "manifest_count=[llength $manifest_names]"
puts $out "post_dft_scan_cell_count=1024"
puts $out "chain_count_requested=1"
foreach_in_collection cell $selected_after { puts $out [get_object_name $cell] }
close $out
exit
