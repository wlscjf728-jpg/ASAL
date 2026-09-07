# Resolve the compact role selectors against mapped register-cell names.
set ALL_CELLS [get_cells -hierarchical *]

proc matching_names {pattern} {
  global ALL_CELLS
  set names {}
  foreach_in_collection cell $ALL_CELLS {
    set name [get_object_name $cell]
    if {[regexp -- $pattern $name]} {
      lappend names $name
    }
  }
  return [lsort -dictionary $names]
}

proc collection_for_names {names} {
  global ALL_CELLS
  set result [remove_from_collection $ALL_CELLS $ALL_CELLS]
  foreach_in_collection cell $ALL_CELLS {
    if {[lsearch -exact $names [get_object_name $cell]] >= 0} {
      set result [add_to_collection $result $cell]
    }
  }
  return $result
}

proc require_count {label names expected} {
  if {[llength $names] < $expected} {
    error "$label requires $expected cells but found [llength $names]"
  }
  return [lrange $names 0 [expr {$expected - 1}]]
}

set target_names [matching_names {MC_REG.*\[36\]}]
set target_names [require_count target_mc36 $target_names 1]
set state_names [matching_names {STATE_REG.*\[[0-9]+\]}]
set state_names [require_count aes_state_decoys $state_names 127]
set data_names [matching_names {data_control_decoy_reg.*\[[0-9]+\]}]
set data_names [require_count data_control_decoys $data_names 120]
set status_names [matching_names {status_control_decoy_reg.*\[[0-9]+\]}]
set status_names [require_count status_control_decoys $status_names 8]

set selected_names [concat $target_names $state_names $data_names $status_names]
if {[llength $selected_names] != 256} {
  error "selected scan population is not 256"
}
if {[llength [lsort -unique $selected_names]] != 256} {
  error "selected scan population contains duplicate cell names"
}

set selected [collection_for_names $selected_names]
if {[sizeof_collection $selected] != 256} {
  error "selected cell collection did not contain 256 cells"
}
