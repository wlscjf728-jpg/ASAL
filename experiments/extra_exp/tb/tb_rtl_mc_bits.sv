`timescale 1ns/1ps
module tb_rtl_mc_bits;
 reg clk=0,reset_n=0,start=0; reg [127:0] plaintext=0,key=0; wire busy,done; wire [127:0] ciphertext; wire [3:0] round; wire [2:0] phase;

 function automatic [127:0] pack_semantic; input [127:0] value; integer bi,bidx; begin pack_semantic=0; for(bi=0;bi<16;bi=bi+1) for(bidx=0;bidx<8;bidx=bidx+1) pack_semantic[8*bi+bidx]=value[127-8*bi-bidx]; end endfunction
 aes128_iterative_mc_boundary dut(.*); always #5 clk=~clk;
 initial begin
  repeat(2) @(negedge clk); reset_n=1; @(negedge clk); plaintext=128'h00000000000000000000000000000000; key=128'ha66f651322597191ab9f8f8af4c2db61; start=1; @(posedge clk); #1; start=0;
  wait(round==2); #1; $display("rtl mc=%h expected=%h mc9=%b mc14=%b",dut.MC_REG,pack_semantic(128'h92d323118f93a636677e45d75b74c82d),dut.MC_REG[9],dut.MC_REG[14]); $finish;
 end
endmodule
