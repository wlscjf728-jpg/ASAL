// TetraMAX model for the generic sequential cell emitted by DC functional export.
module \**SEQGEN** (
  clear, preset, next_state, clocked_on, data_in, enable, Q,
  synch_clear, synch_preset, synch_toggle, synch_enable
);
  input clear, preset, clocked_on, data_in, enable;
  input synch_clear, synch_preset, synch_toggle, synch_enable;
  input next_state;
  output Q;
  reg Q;
  always @(posedge clocked_on or posedge clear or posedge preset) begin
    if (clear) Q <= 1'b0;
    else if (preset) Q <= 1'b1;
    else if (synch_clear) Q <= 1'b0;
    else if (synch_preset) Q <= 1'b1;
    else if (synch_toggle) Q <= ~Q;
    else if (synch_enable || enable) Q <= next_state;
    else Q <= Q;
  end
endmodule
