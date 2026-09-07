`timescale 1ns/1ps
`default_nettype none

module tb_aes128_mc_trace;
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
  integer failures = 0;

  function automatic [127:0] pack_semantic;
    input [127:0] value;
    integer byte_index;
    integer bit_index;
    begin
      pack_semantic = 128'h0;
      for (byte_index = 0; byte_index < 16; byte_index = byte_index + 1)
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
          pack_semantic[8*byte_index + bit_index] =
            value[127 - 8*byte_index - (7 - bit_index)];
    end
  endfunction

  aes128_iterative_mc_boundary dut(.*);
  always #5 clk = ~clk;

  task automatic run_trace;
    input [127:0] in_plaintext;
    input [127:0] expected_mc1;
    input [127:0] expected_mc2;
    input [127:0] expected_ciphertext;
    begin
      @(negedge clk);
      plaintext = in_plaintext;
      key = 128'ha66f651322597191ab9f8f8af4c2db61;
      start = 1'b1;
      @(posedge clk);
      #1;
      start = 1'b0;
      wait (dut.ROUND_REG == 4'd2);
      #1;
      if (dut.MC_REG !== pack_semantic(expected_mc1)) begin
        $display("MC1_FAIL p=%h got=%h expected_packed=%h", in_plaintext, dut.MC_REG, pack_semantic(expected_mc1));
        failures = failures + 1;
      end
      @(posedge clk);
      #1;
      if (dut.MC_REG !== pack_semantic(expected_mc2)) begin
        $display("MC2_FAIL p=%h got=%h expected_packed=%h", in_plaintext, dut.MC_REG, pack_semantic(expected_mc2));
        failures = failures + 1;
      end
      wait (done);
      #1;
      if (ciphertext !== expected_ciphertext) begin
        $display("CIPHER_FAIL p=%h got=%h expected=%h", in_plaintext, ciphertext, expected_ciphertext);
        failures = failures + 1;
      end
    end
  endtask

  initial begin
    repeat (2) @(negedge clk);
    reset_n = 1'b1;
    run_trace(128'h00000000000000000000000000000000,
      128'h92d323118f93a636677e45d75b74c82d,
      128'hf8b4d2006fde15d1345db451b39bd147,
      128'hb1a97b984d02b0dc9b935cdacf524f76);
    @(negedge clk);
    reset_n = 1'b0;
    @(negedge clk);
    reset_n = 1'b1;
    run_trace(128'h00000000005200000000000000000000,
      128'ha908c3f18f93a636677e45d75b74c82d,
      128'h8e8fe94d59e84fbddc7e7fb92977a731,
      128'h7fe284ff2d32ab42a04f75d24a7a736f);
    @(negedge clk);
    reset_n = 1'b0;
    @(negedge clk);
    reset_n = 1'b1;
    run_trace(128'hf4000000004800d86000586000cb0010,
      128'h30ae60d18f93a6364bf1c91ba28dd8c4,
      128'h62531f36330506d7f435ae059a6ac01d,
      128'hec5bd5c1892eef48fb978da732addac3);
    if (failures != 0) $fatal(1, "MC trace failures=%0d", failures);
    $display("RTL_MC_TRACE_PASS");
    $finish;
  end
endmodule

`default_nettype wire
