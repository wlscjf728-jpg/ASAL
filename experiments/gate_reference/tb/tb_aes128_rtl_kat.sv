`timescale 1ns/1ps
`default_nettype none

module tb_aes128_rtl_kat;
  reg clk = 1'b0;
  reg reset_n = 1'b0;
  reg start = 1'b0;
  reg [127:0] plaintext = 128'h0;
  reg [127:0] key = 128'h0;
  wire busy;
  wire done;
  wire [127:0] ciphertext;
  wire [3:0] round;
  wire [2:0] phase;

  aes128_iterative_mc_boundary dut(.*);
  always #5 clk = ~clk;

  task automatic run_case;
    input [127:0] in_plaintext;
    input [127:0] in_key;
    input [127:0] expected_ciphertext;
    begin
      @(negedge clk);
      plaintext = in_plaintext;
      key = in_key;
      start = 1'b1;
      @(negedge clk);
      start = 1'b0;
      wait (done);
      if (ciphertext !== expected_ciphertext) begin
        $display("KAT_FAIL got=%h expected=%h", ciphertext, expected_ciphertext);
        $fatal(1);
      end
      @(negedge clk);
    end
  endtask

  initial begin
    repeat (2) @(negedge clk);
    reset_n = 1'b1;
    run_case(128'h00112233445566778899aabbccddeeff,
             128'h000102030405060708090a0b0c0d0e0f,
             128'h69c4e0d86a7b0430d8cdb78070b4c55a);
    $display("RTL_AES128_KAT_PASS");
    $finish;
  end
endmodule

`default_nettype wire
