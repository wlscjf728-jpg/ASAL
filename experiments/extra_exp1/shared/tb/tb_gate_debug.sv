`timescale 1ns/1ps
module tb_gate_debug;
 reg clk=0, reset_n=0, start=0, test_mode=0, scan_en=0, scan_in=0, scan_capture=0;
 reg [127:0] plaintext=0, key=0;
 wire scan_out,busy,done; wire [127:0] ciphertext,decoy_observe; wire [7:0] status_observe;
 extra_exp_top dut(.*);
 always #5 clk=~clk;
 integer i;
 initial begin
   $monitor("t=%0t rst=%b start=%b busy=%b done=%b c=%h phase=%b round=%b scan=%b cp=%b n314=%b n333=%b clk=%b", $time,reset_n,start,busy,done,ciphertext,dut.aes_core.phase,dut.aes_core.round,scan_out,dut.aes_core.n293,dut.aes_core.n314,dut.aes_core.n333,clk);
   #20; reset_n=1;
   #10; plaintext=128'h00000000000000000000000000000000; key=128'ha66f651322597191ab9f8f8af4c2db61; start=1;
   #10; start=0;
   repeat(1) @(posedge clk); $display("AFTER_MC mc9=%b d=%b state=%h",dut.aes_core.n10711,dut.aes_core.n9502,dut.aes_core.STATE_REG);
   repeat(1) @(posedge clk); $display("AFTER_UPDATE mc9=%b d=%b state=%h",dut.aes_core.n10711,dut.aes_core.n9502,dut.aes_core.STATE_REG);
   repeat(1) @(posedge clk); $display("AFTER_MC2 mc9=%b d=%b state=%h",dut.aes_core.n10711,dut.aes_core.n9502,dut.aes_core.STATE_REG);
   repeat(100) @(posedge clk);
   $display("DEBUG_DONE busy=%b done=%b cipher=%h",busy,done,ciphertext);
   $finish;
 end
endmodule
