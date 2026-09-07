`timescale 1ns/1ps

module tb_gate_verdi_evidence;
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
  wire busy;
  wire done;
  wire [127:0] ciphertext;
  wire [127:0] decoy_observe;
  wire [7:0] status_observe;

  extra_exp_top dut(.*);
  always #5 clk = ~clk;

  integer i;
  integer schedule;
  integer query_id;
  integer shift_count;
  integer shift_limit;
  integer marker_fd;
  reg [127:0] secret;
  reg [127:0] p0;
  reg [127:0] p1;
  reg [1023:0] fsdb_path;
  reg [1023:0] marker_path;
  reg [1023:0] case_name;
  reg [7:0] evidence_bus;

  always @(*) begin
    evidence_bus = {scan_en, scan_in, scan_out, reset_n, start, busy, done, scan_capture};
  end

  task automatic launch(input [127:0] value);
    begin
      reset_n = 1'b0;
      start = 1'b0;
      scan_en = 1'b0;
      scan_in = 1'b0;
      repeat (2) @(negedge clk);
      reset_n = 1'b1;
      @(negedge clk);
      plaintext = value;
      key = secret;
      start = 1'b1;
      @(negedge clk);
      start = 1'b0;
    end
  endtask

  task automatic capture_schedule(input integer q, input integer s);
    begin
      repeat (s) @(posedge clk);
      #1;
      $fdisplay(marker_fd, "%0t functional query=%0d schedule=%0d target_q=%b scan_out=%b evidence_bus=%b",
                $time, q, s, dut.aes_core.n10857, scan_out, evidence_bus);
      scan_en = 1'b1;
      scan_in = 1'b0;
      for (shift_count = 0; shift_count < shift_limit; shift_count = shift_count + 1) begin
        #1;
        if (shift_count == 0 || shift_count == shift_limit - 1)
          $fdisplay(marker_fd, "%0t shift query=%0d schedule=%0d count=%0d target_q=%b scan_out=%b evidence_bus=%b",
                    $time, q, s, shift_count, dut.aes_core.n10857, scan_out, evidence_bus);
        @(posedge clk);
        @(negedge clk);
      end
      scan_en = 1'b0;
      scan_in = 1'b0;
    end
  endtask

  task automatic run_plaintext_pair(input integer first_schedule, input integer last_schedule);
    begin
      for (query_id = 0; query_id < 2; query_id = query_id + 1) begin
        launch(query_id == 0 ? p0 : p1);
        for (schedule = first_schedule; schedule <= last_schedule; schedule = schedule + 1)
          capture_schedule(query_id, schedule);
      end
    end
  endtask

  task automatic run_walking_one;
    begin
      reset_n = 1'b0;
      scan_en = 1'b0;
      scan_in = 1'b0;
      repeat (2) @(negedge clk);
      reset_n = 1'b1;
      @(negedge clk);
      scan_en = 1'b1;
      for (shift_count = 0; shift_count < 256; shift_count = shift_count + 1) begin
        scan_in = (shift_count == 0);
        #1;
        $fdisplay(marker_fd, "%0t walking_one count=%0d scan_in=%b scan_out=%b target_q=%b evidence_bus=%b",
                  $time, shift_count, scan_in, scan_out, dut.aes_core.n10857, evidence_bus);
        @(posedge clk);
        @(negedge clk);
      end
      scan_en = 1'b0;
      scan_in = 1'b0;
    end
  endtask

  initial begin
    if (!$value$plusargs("FSDB=%s", fsdb_path)) $fatal(1, "FSDB missing");
    if (!$value$plusargs("MARKER=%s", marker_path)) $fatal(1, "MARKER missing");
    if (!$value$plusargs("CASE=%s", case_name)) $fatal(1, "CASE missing");
    marker_fd = $fopen(marker_path, "w");
    shift_limit = (case_name == "scan_shift_identity") ? 256 : 1;
    if (!marker_fd) $fatal(1, "cannot open marker file");
    $fsdbDumpfile(fsdb_path);
    $fsdbDumpvars(0, dut.aes_core.n10857);
    $fsdbDumpvars(0, scan_out);
    $fsdbDumpvars(0, evidence_bus);
    $fdisplay(marker_fd, "case=%s fsdb=%s selected_slot=255", case_name, fsdb_path);

    if ($test$plusargs("WALKING")) begin
      run_walking_one();
    end else begin
      if (!$value$plusargs("KEY_HEX=%h", secret)) $fatal(1, "KEY_HEX missing");
      if (!$value$plusargs("P0=%h", p0)) $fatal(1, "P0 missing");
      if (!$value$plusargs("P1=%h", p1)) $fatal(1, "P1 missing");
      if (case_name == "phase0_mc_slot_discovery") run_plaintext_pair(1, 3);
      else if (case_name == "phase1_q30_depth2") run_plaintext_pair(1, 3);
      else if (case_name == "phase2_separator") run_plaintext_pair(1, 3);
      else run_plaintext_pair(1, 3);
    end

    $fdisplay(marker_fd, "VERDI_TRACE_DONE case=%s", case_name);
    $fclose(marker_fd);
    $fsdbDumpoff;
    $finish;
  end
endmodule
