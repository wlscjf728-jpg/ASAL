`timescale 1ns/1ps
`default_nettype none

module tb_gate_capture;
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

  integer qfd;
  integer ofd;
  integer qid;
  integer rc;
  integer i;
  reg [255:0] scan_vector;
  reg [127:0] secret_key;
  reg [127:0] current_plaintext;
  reg target_value;
  reg [1023:0] query_path;
  reg [1023:0] output_path;
  reg start_enabled;

  task automatic reset_and_launch(input [127:0] p);
    begin
      scan_en = 1'b0;
      scan_in = 1'b0;
      scan_capture = 1'b0;
      start = 1'b0;
      reset_n = 1'b0;
      repeat (2) @(negedge clk);
      reset_n = 1'b1;
      @(negedge clk);
      plaintext = p;
      key = secret_key;
      if (start_enabled) begin
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;
      end
    end
  endtask

  task automatic shift_out(output [255:0] value);
    begin
      value = 256'h0;
      @(negedge clk);
      target_value = 1'b0;
      scan_en = 1'b1;
      scan_in = 1'b0;
      for (i = 0; i < 256; i = i + 1) begin
        #1 value[i] = scan_out;
        @(posedge clk);
        @(negedge clk);
      end
      scan_en = 1'b0;
    end
  endtask

  task automatic emit(input integer id, input integer schedule, input [255:0] value);
    begin
      $fwrite(ofd, "%0d %0d %0d %064h\n", id, schedule, target_value, value);
    end
  endtask

  initial begin
    if (!$value$plusargs("QUERY_FILE=%s", query_path)) $fatal(1, "QUERY_FILE missing");
    if (!$value$plusargs("OUT_FILE=%s", output_path)) $fatal(1, "OUT_FILE missing");
    if (!$value$plusargs("KEY_HEX=%h", secret_key)) $fatal(1, "KEY_HEX missing");
    start_enabled = !$test$plusargs("NO_START");
    qfd = $fopen(query_path, "r");
    ofd = $fopen(output_path, "w");
    if (!qfd || !ofd) $fatal(1, "cannot open query/output file");

    while (!$feof(qfd)) begin
      rc = $fscanf(qfd, "%d %h\n", qid, current_plaintext);
      if (rc == 2) begin
        // Fixed schedule: start capture, round-1 MC boundary, round-1
        // update boundary, then round-2 MC boundary.
        reset_and_launch(current_plaintext);
        @(posedge clk);
        shift_out(scan_vector);
        emit(qid, 1, scan_vector);

        reset_and_launch(current_plaintext);
        repeat (2) @(posedge clk);
        shift_out(scan_vector);
        emit(qid, 2, scan_vector);

        reset_and_launch(current_plaintext);
        repeat (3) @(posedge clk);
        shift_out(scan_vector);
        emit(qid, 3, scan_vector);
      end
    end
    $fclose(qfd);
    $fclose(ofd);
    $display("GATE_CAPTURE_DONE");
    $finish;
  end
endmodule

`default_nettype wire
