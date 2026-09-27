`timescale 1ns/1ps
`default_nettype none

module tb_gate_scan_calibration;
  reg clk = 1'b0;
  reg reset_n = 1'b0;
  reg start = 1'b0;
  reg test_mode = 1'b1;
  reg scan_en = 1'b0;
  reg scan_in = 1'b0;
  reg scan_capture = 1'b0;
  reg [127:0] plaintext = 128'h0;
  reg [127:0] key = 128'h0;
  wire scan_out;
  wire busy, done;
  wire [127:0] ciphertext, decoy_observe;
  wire [7:0] status_observe;

  extra_exp_top dut(.*);
  always #5 clk = ~clk;

  integer fd;
  integer i;
  reg [255:0] pattern;

  initial begin
    fd = $fopen("extra_exp/results/phase_b/scan_calibration.txt", "w");
    if (!fd) $fatal(1, "cannot open scan calibration output");
    pattern = 256'h0;
    reset_n = 1'b0;
    repeat (2) @(negedge clk);
    reset_n = 1'b1;
    // A deterministic alternating pattern makes the serializer direction
    // observable without exposing any semantic signal to the TB consumer.
    for (i = 0; i < 256; i = i + 1) pattern[i] = (i % 2);
    @(negedge clk);
    scan_en = 1'b1;
    for (i = 0; i < 256; i = i + 1) begin
      scan_in = pattern[i];
      @(posedge clk);
    end
    @(negedge clk);
    scan_in = 1'b0;
    for (i = 0; i < 256; i = i + 1) begin
      #1 $fwrite(fd, "%0d %0d\n", i, scan_out);
      @(posedge clk);
      @(negedge clk);
    end
    scan_en = 1'b0;
    $fclose(fd);
    $display("GATE_SCAN_CALIBRATION_PASS");
    $finish;
  end
endmodule

`default_nettype wire
