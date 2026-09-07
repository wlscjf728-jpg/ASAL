# Common synthesis settings shared by every DFT branch.
set ROOT [file normalize [file join [file dirname [info script]] ..]]
set TARGET_LIBRARY $ROOT/config/class_scan.db
set_app_var search_path [concat $search_path [list $ROOT/rtl $ROOT/rtl/mor1kx]]
set_app_var target_library [list $TARGET_LIBRARY]
set_app_var link_library [list * $TARGET_LIBRARY]
set_app_var hdlin_enable_vpp true
set_app_var verilogout_no_tri true
set_app_var verilogout_single_bit false

file mkdir $ROOT/results
file mkdir $ROOT/results/checkpoint
file mkdir $ROOT/reports
file mkdir $ROOT/logs
