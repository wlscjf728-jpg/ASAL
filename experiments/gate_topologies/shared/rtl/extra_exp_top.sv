`default_nettype none

module extra_exp_top(
  input  wire         clk,
  input  wire         reset_n,
  input  wire         start,
  input  wire [127:0] plaintext,
  input  wire [127:0] key,
  input  wire         test_mode,
  input  wire         scan_en,
  input  wire         scan_in,
  input  wire         scan_capture,
  output wire         scan_out,
  output wire         busy,
  output wire         done,
  output wire [127:0] ciphertext,
  output wire [127:0] decoy_observe,
  output wire [7:0]   status_observe
);
  wire [3:0] round;
  wire [2:0] phase;

  aes128_iterative_mc_boundary aes_core(
    .clk(clk), .reset_n(reset_n), .start(start),
    .plaintext(plaintext), .key(key), .busy(busy), .done(done),
    .ciphertext(ciphertext), .round(round), .phase(phase)
  );

  scan_decoy_bank decoy_bank(
    .clk(clk), .reset_n(reset_n), .enable(start | busy | scan_capture),
    .seed(plaintext), .data_observe(decoy_observe), .status_observe(status_observe)
  );

  // These ports are consumed by DFT Compiler after synthesis. Keeping them
  // explicit also makes the gate-level testbench interface stable.
  wire unused_test_mode = test_mode;
  wire unused_scan_in = scan_in;
  wire unused_scan_capture = scan_capture;
  assign scan_out = unused_test_mode ^ unused_scan_in ^ unused_scan_capture ^ 1'b0;
endmodule

`default_nettype wire
