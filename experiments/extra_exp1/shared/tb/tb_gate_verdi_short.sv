`timescale 1ns/1ps
module tb_gate_verdi_short;
 reg clk=0,reset_n=0,start=0,test_mode=1,scan_en=0,scan_in=0,scan_capture=0; reg [127:0] plaintext=0,key=0;
 wire scan_out,busy,done; wire [127:0] ciphertext,decoy_observe; wire [7:0] status_observe;
 extra_exp_top dut(.*); always #5 clk=~clk;
 integer i; reg [127:0] secret;
 task launch(input [127:0] x); begin reset_n=0;start=0;scan_en=0;repeat(2) @(negedge clk);reset_n=1;@(negedge clk);plaintext=x;key=secret;start=1;@(negedge clk);start=0; end endtask
 task scan_now; begin @(negedge clk);scan_en=1;scan_in=0;for(i=0;i<16;i=i+1) begin #1;@(posedge clk);@(negedge clk);end scan_en=0; end endtask
 initial begin
  secret=128'ha66f651322597191ab9f8f8af4c2db61;
  $fsdbDumpfile("extra_exp/results/verdi/mc9_trace_short.fsdb"); $fsdbDumpvars(0,dut.aes_core.n10857); $fsdbDumpvars(0,dut.scan_out);
  launch(128'h00000000000000000000000000000000); repeat(1) @(posedge clk); #1; $display("VERDI_MARKER q0 schedule=1 mc9_q=%b scan_out=%b",dut.aes_core.n10857,scan_out);
  scan_en=1; scan_in=0; #1; $display("VERDI_SCAN_ENABLE scan_out=%b",scan_out); scan_en=0;
  $fsdbDumpoff; $display("VERDI_TRACE_DONE"); $finish;
 end
endmodule
