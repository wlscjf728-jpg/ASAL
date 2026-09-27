`timescale 1ns/1ps
`default_nettype none

module tb_scan_integrity;
  reg clk = 1'b0;
  reg reset_n = 1'b0;
  reg start = 1'b0;
  reg test_mode = 1'b0;
  reg scan_en = 1'b0;
  reg scan_in = 1'b0;
  reg scan_capture = 1'b0;
  reg [127:0] plaintext = 128'h0;
  reg [127:0] key = 128'h0;
  wire scan_out;
  wire busy;
  wire done;
  wire [127:0] ciphertext;
  wire [127:0] decoy_observe;
  wire [7:0] status_observe;

  extra_exp_top dut(.*);
  always #5 clk = ~clk;

  initial begin
    repeat (2) @(negedge clk);
    reset_n = 1'b1;
    @(negedge clk);
    plaintext = 128'h00112233445566778899aabbccddeeff;
    key = 128'h000102030405060708090a0b0c0d0e0f;
    start = 1'b1;
    @(negedge clk);
    start = 1'b0;
    wait (done);
    #1;
    if (ciphertext !== 128'h69c4e0d86a7b0430d8cdb78070b4c55a)
      $fatal(1, "pre-DFT functional KAT failed: %h", ciphertext);
    $display("PRESCAN_FUNCTIONAL_KAT_PASS");
    $finish;
  end
endmodule

`default_nettype wire
