`default_nettype none

module scan_decoy_bank(
  input  wire         clk,
  input  wire         reset_n,
  input  wire         enable,
  input  wire [127:0] seed,
  output wire [127:0] data_observe,
  output wire [7:0]   status_observe
);
  (* keep = "true" *) reg data_control_decoy_reg [0:119];
  (* keep = "true" *) reg status_control_decoy_reg [0:7];
  integer i;

  always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
      for (i = 0; i < 120; i = i + 1)
        data_control_decoy_reg[i] <= 1'b0;
      for (i = 0; i < 8; i = i + 1)
        status_control_decoy_reg[i] <= 1'b0;
    end else if (enable) begin
      for (i = 0; i < 120; i = i + 1)
        data_control_decoy_reg[i] <= seed[i] ^ seed[(i + 1) % 128];
      for (i = 0; i < 8; i = i + 1)
        status_control_decoy_reg[i] <= seed[i] ^ enable;
    end
  end

  genvar data_index;
  generate
    for (data_index = 0; data_index < 120; data_index = data_index + 1) begin : GEN_DATA_OBSERVE
      assign data_observe[data_index] = data_control_decoy_reg[data_index];
    end
  endgenerate

  genvar status_index;
  generate
    for (status_index = 0; status_index < 8; status_index = status_index + 1) begin : GEN_STATUS_OBSERVE
      assign status_observe[status_index] = status_control_decoy_reg[status_index];
    end
  endgenerate
endmodule

`default_nettype wire
