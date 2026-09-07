`timescale 1ns/1ps
module tb_gate_target_sweep;
 reg clk=0,reset_n=0,start=0,test_mode=0,scan_en=0,scan_in=0,scan_capture=0; reg [127:0] plaintext=0,key=0;
 wire scan_out,busy,done; wire [127:0] ciphertext,decoy_observe; wire [7:0] status_observe; extra_exp_top dut(.*); always #5 clk=~clk;
 integer qfd,ofd,qid,rc,s; reg [127:0] p,secret; reg [1023:0] qpath,opath;
 task launch(input [127:0] x); begin reset_n=0; start=0; scan_en=0; repeat(2) @(negedge clk); reset_n=1; @(negedge clk); plaintext=x; key=secret; start=1; @(negedge clk); start=0; end endtask
 initial begin
  if(!$value$plusargs("QUERY_FILE=%s",qpath)) $fatal; if(!$value$plusargs("OUT_FILE=%s",opath)) $fatal; if(!$value$plusargs("KEY_HEX=%h",secret)) $fatal;
  qfd=$fopen(qpath,"r"); ofd=$fopen(opath,"w");
  while(!$feof(qfd)) begin rc=$fscanf(qfd,"%d %h\n",qid,p); if(rc==2) begin for(s=1;s<=12;s=s+1) begin launch(p); repeat(s) @(posedge clk); #1; $fwrite(ofd,"%0d %0d %0d\n",qid,s,dut.aes_core.n10857); end end end
  $fclose(qfd);$fclose(ofd);$display("GATE_TARGET_SWEEP_DONE");$finish;
 end
endmodule
