# Standalone MC9 pre-DFT synthesis.
set EXTRA_ROOT [file normalize [file join [file dirname [info script]] ..]]
set PROJECT_ROOT [file normalize [file join $EXTRA_ROOT ..]]
set LIBRARY "/srscl/home/jcjeong/Research/Scan_Secure/experiments/RTL/config/class_scan.db"
set RTL_FILES [list \
  [file join "/srscl/home/jcjeong/Research/Scan_Secure/experiments/extra_exp1/shared/rtl" aes_sbox.v] \
  [file join "/srscl/home/jcjeong/Research/Scan_Secure/experiments/extra_exp1/shared/rtl" aes128_iterative_mc_boundary.sv] \
  [file join "/srscl/home/jcjeong/Research/Scan_Secure/experiments/extra_exp1/shared/rtl" scan_decoy_bank.sv] \
  [file join "/srscl/home/jcjeong/Research/Scan_Secure/experiments/extra_exp1/shared/rtl" extra_exp_top.sv] \
]

set_app_var search_path [list [file join "/srscl/home/jcjeong/Research/Scan_Secure/experiments/extra_exp1/shared/rtl"] [file join $PROJECT_ROOT RTL rtl]]
set_app_var target_library [list $LIBRARY]
set_app_var link_library [list * $LIBRARY]
set_app_var hdlin_enable_vpp true
set_app_var verilogout_no_tri true
set_app_var verilogout_single_bit false
set_app_var verilogout_show_unconnected_pins true

file mkdir [file join $EXTRA_ROOT netlist]
file mkdir [file join $EXTRA_ROOT results evaluator]
file mkdir [file join $EXTRA_ROOT logs]
define_design_lib WORK -path [file join $EXTRA_ROOT results dc_work]
analyze -format sverilog $RTL_FILES
elaborate extra_exp_top
current_design extra_exp_top
link

# Preserve hierarchy while allowing the selected registers to map to the
# library scan-compatible flip-flop cells.
set hier_designs [get_designs -hierarchical *]
catch {set_ungroup $hier_designs false}
compile -map_effort medium

set reg_rpt [open [file join $EXTRA_ROOT results evaluator register_inventory_prescan.rpt] w]
set regs [all_registers]
puts $reg_rpt "register_count=[sizeof_collection $regs]"
foreach reg [get_object_name $regs] { puts $reg_rpt $reg }
close $reg_rpt
redirect -file [file join $EXTRA_ROOT results evaluator functional_prescan.rpt] {
  report_area
  report_timing
}
write -format verilog -hierarchy -output [file join $EXTRA_ROOT netlist extra_exp_prescan.v]
write -format ddc -hierarchy -output [file join $EXTRA_ROOT netlist extra_exp_prescan.ddc]
exit
