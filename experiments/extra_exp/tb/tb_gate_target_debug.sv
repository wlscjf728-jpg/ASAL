`timescale 1ns/1ps
module tb_gate_target_debug;
 reg clk=0,reset_n=0,start=0,test_mode=0,scan_en=0,scan_in=0,scan_capture=0;
 reg [127:0] plaintext=0,key=0;
 wire scan_out,busy,done; wire [127:0] ciphertext,decoy_observe; wire [7:0] status_observe;
 extra_exp_top dut(.*);
 always #5 clk=~clk;
 task run(input [127:0] p);
   integer k;
   begin
    reset_n=0; start=0; scan_en=0; repeat(2) @(negedge clk); reset_n=1; @(negedge clk);
    plaintext=p; key=128'ha66f651322597191ab9f8f8af4c2db61; start=1; @(negedge clk); start=0;
    for(k=0;k<5;k=k+1) begin
      @(negedge clk); #1;
      $display("p=%h pre_edge=%0d q=%b d=%b cp=%b cd=%b busy=%b r=%h ph=%h",p,k,dut.aes_core.n10857,dut.aes_core.n10229,dut.aes_core.n363,dut.aes_core.n294,busy,dut.aes_core.round,dut.aes_core.phase);
      @(posedge clk); #1;
      $display("p=%h post_edge=%0d q=%b d=%b cp=%b cd=%b busy=%b r=%h ph=%h",p,k,dut.aes_core.n10857,dut.aes_core.n10229,dut.aes_core.n363,dut.aes_core.n294,busy,dut.aes_core.round,dut.aes_core.phase);
    end
   end
 endtask
 initial begin
  run(128'h01000000000000000000000000000000);
  $finish;
 end
endmodule
