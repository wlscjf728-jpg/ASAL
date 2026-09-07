`default_nettype none

module aes128_iterative_mc_boundary(
  input  wire         clk,
  input  wire         reset_n,
  input  wire         start,
  input  wire [127:0] plaintext,
  input  wire [127:0] key,
  output wire         busy,
  output wire         done,
  output wire [127:0] ciphertext,
  output wire [3:0]   round,
  output wire [2:0]   phase
);
  localparam [2:0] PHASE_IDLE = 3'd0;
  localparam [2:0] PHASE_MC = 3'd1;
  localparam [2:0] PHASE_UPDATE = 3'd2;
  localparam [2:0] PHASE_FINAL = 3'd3;
  localparam [2:0] PHASE_DONE = 3'd4;

  reg [127:0] STATE_REG;
  reg [127:0] KEY_REG;
  reg [127:0] MC_REG;
  reg [127:0] CIPHERTEXT_REG;
  reg [3:0] ROUND_REG;
  reg [2:0] PHASE_REG;
  reg BUSY_REG;
  reg DONE_REG;

  wire [127:0] SB_STATE;
  wire [127:0] SR_STATE;
  wire [127:0] MC_STATE;
  wire [127:0] NEXT_KEY;
  wire [127:0] FINAL_STATE;

  genvar sbox_index;
  generate
    for (sbox_index = 0; sbox_index < 16; sbox_index = sbox_index + 1) begin : GEN_SBOX
      aes_sbox_byte u_sbox(
        .in_byte(STATE_REG[127 - sbox_index*8 -: 8]),
        .out_byte(SB_STATE[127 - sbox_index*8 -: 8])
      );
    end
  endgenerate

  function automatic [127:0] shift_rows;
    input [127:0] value;
    integer row;
    integer column;
    integer destination;
    integer source;
    begin
      shift_rows = 128'h0;
      for (row = 0; row < 4; row = row + 1) begin
        for (column = 0; column < 4; column = column + 1) begin
          destination = 4*column + row;
          source = 4*((column + row) % 4) + row;
          shift_rows[127 - destination*8 -: 8] = value[127 - source*8 -: 8];
        end
      end
    end
  endfunction

  // The attack manifests use byte-major, little-endian bit indices
  // (byte 1 bit 1 is semantic index 9). MC_REG uses the same byte-major,
  // little-endian bit numbering so physical MC_REG[9] is the historical MC_9 tap.
  function automatic [127:0] pack_semantic_state;
    input [127:0] value;
    integer byte_index;
    integer bit_index;
    begin
      pack_semantic_state = 128'h0;
      for (byte_index = 0; byte_index < 16; byte_index = byte_index + 1)
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
          pack_semantic_state[8*byte_index + bit_index] =
            value[127 - 8*byte_index - (7 - bit_index)];
    end
  endfunction

  function automatic [127:0] unpack_semantic_state;
    input [127:0] value;
    integer byte_index;
    integer bit_index;
    begin
      unpack_semantic_state = 128'h0;
      for (byte_index = 0; byte_index < 16; byte_index = byte_index + 1)
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
          unpack_semantic_state[127 - 8*byte_index - (7 - bit_index)] =
            value[8*byte_index + bit_index];
    end
  endfunction

  function automatic [7:0] xtime;
    input [7:0] value;
    begin
      xtime = value[7] ? ((value << 1) ^ 8'h1b) : (value << 1);
    end
  endfunction

  function automatic [31:0] mix_column;
    input [31:0] value;
    reg [7:0] a0;
    reg [7:0] a1;
    reg [7:0] a2;
    reg [7:0] a3;
    reg [7:0] x0;
    reg [7:0] x1;
    reg [7:0] x2;
    reg [7:0] x3;
    begin
      a0 = value[31:24];
      a1 = value[23:16];
      a2 = value[15:8];
      a3 = value[7:0];
      x0 = xtime(a0);
      x1 = xtime(a1);
      x2 = xtime(a2);
      x3 = xtime(a3);
      mix_column[31:24] = x0 ^ (x1 ^ a1) ^ a2 ^ a3;
      mix_column[23:16] = a0 ^ x1 ^ (x2 ^ a2) ^ a3;
      mix_column[15:8] = a0 ^ a1 ^ x2 ^ (x3 ^ a3);
      mix_column[7:0] = (x0 ^ a0) ^ a1 ^ a2 ^ x3;
    end
  endfunction

  function automatic [127:0] mix_columns;
    input [127:0] value;
    integer column;
    begin
      mix_columns = 128'h0;
      for (column = 0; column < 4; column = column + 1) begin
        mix_columns[127 - column*32 -: 32] =
          mix_column(value[127 - column*32 -: 32]);
      end
    end
  endfunction

  function automatic [7:0] rcon;
    input [3:0] round_number;
    begin
      case (round_number)
        4'd1: rcon = 8'h01;
        4'd2: rcon = 8'h02;
        4'd3: rcon = 8'h04;
        4'd4: rcon = 8'h08;
        4'd5: rcon = 8'h10;
        4'd6: rcon = 8'h20;
        4'd7: rcon = 8'h40;
        4'd8: rcon = 8'h80;
        4'd9: rcon = 8'h1b;
        4'd10: rcon = 8'h36;
        default: rcon = 8'h00;
      endcase
    end
  endfunction

  function automatic [127:0] expand_key;
    input [127:0] value;
    input [3:0] round_number;
    reg [7:0] old_byte [0:15];
    reg [7:0] new_byte [0:15];
    reg [7:0] t0;
    reg [7:0] t1;
    reg [7:0] t2;
    reg [7:0] t3;
    integer i;
    begin
      for (i = 0; i < 16; i = i + 1)
        old_byte[i] = value[127 - i*8 -: 8];
      t0 = old_byte[13];
      t1 = old_byte[14];
      t2 = old_byte[15];
      t3 = old_byte[12];
      t0 = aes_key_sbox(t0);
      t1 = aes_key_sbox(t1);
      t2 = aes_key_sbox(t2);
      t3 = aes_key_sbox(t3);
      t0 = t0 ^ rcon(round_number);
      for (i = 0; i < 4; i = i + 1)
        new_byte[i] = old_byte[i] ^ (i == 0 ? t0 : i == 1 ? t1 : i == 2 ? t2 : t3);
      for (i = 4; i < 8; i = i + 1)
        new_byte[i] = old_byte[i] ^ new_byte[i-4];
      for (i = 8; i < 12; i = i + 1)
        new_byte[i] = old_byte[i] ^ new_byte[i-4];
      for (i = 12; i < 16; i = i + 1)
        new_byte[i] = old_byte[i] ^ new_byte[i-4];
      expand_key = 128'h0;
      for (i = 0; i < 16; i = i + 1)
        expand_key[127 - i*8 -: 8] = new_byte[i];
    end
  endfunction

  function automatic [7:0] aes_key_sbox;
    input [7:0] value;
    reg [7:0] base;
    reg [7:0] inverse;
    reg [7:0] result;
    integer exponent;
    integer i;
    begin
      if (value == 8'h00) begin
        inverse = 8'h00;
      end else begin
        base = value;
        result = 8'h01;
        exponent = 254;
        for (i = 0; i < 8; i = i + 1) begin
          if (exponent[0]) result = gf_mul(result, base);
          base = gf_mul(base, base);
          exponent = exponent >> 1;
        end
        inverse = result;
      end
      aes_key_sbox = inverse ^ rotl8(inverse, 1) ^ rotl8(inverse, 2) ^
                     rotl8(inverse, 3) ^ rotl8(inverse, 4) ^ 8'h63;
    end
  endfunction

  function automatic [7:0] gf_mul;
    input [7:0] a;
    input [7:0] b;
    reg [7:0] aa;
    reg [7:0] bb;
    reg [7:0] product;
    integer i;
    begin
      aa = a;
      bb = b;
      product = 8'h00;
      for (i = 0; i < 8; i = i + 1) begin
        if (bb[0]) product = product ^ aa;
        aa = aa[7] ? ((aa << 1) ^ 8'h1b) : (aa << 1);
        bb = bb >> 1;
      end
      gf_mul = product;
    end
  endfunction

  function automatic [7:0] rotl8;
    input [7:0] value;
    input integer amount;
    begin
      rotl8 = (value << amount) | (value >> (8 - amount));
    end
  endfunction

  assign SR_STATE = shift_rows(SB_STATE);
  assign MC_STATE = mix_columns(SR_STATE);
  assign NEXT_KEY = expand_key(KEY_REG, ROUND_REG);
  assign FINAL_STATE = SR_STATE ^ NEXT_KEY;

  // Keep the physical MC boundary independent of the phase-control
  // feedback mux.  This makes the captured MC value available on the first
  // MC edge and leaves the old value available to the following ARK update.
  always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
      MC_REG <= 128'h0;
    end else if (BUSY_REG && ROUND_REG < 4'd10) begin
      MC_REG <= pack_semantic_state(MC_STATE);
    end
  end

  always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
      STATE_REG <= 128'h0;
      KEY_REG <= 128'h0;
      CIPHERTEXT_REG <= 128'h0;
      ROUND_REG <= 4'h0;
      PHASE_REG <= PHASE_IDLE;
      BUSY_REG <= 1'b0;
      DONE_REG <= 1'b0;
    end else begin
      DONE_REG <= 1'b0;
      if (start && !BUSY_REG) begin
        STATE_REG <= plaintext ^ key;
        KEY_REG <= key;
        ROUND_REG <= 4'd1;
        PHASE_REG <= PHASE_MC;
        BUSY_REG <= 1'b1;
      end else if (BUSY_REG && ROUND_REG < 4'd10 && PHASE_REG == PHASE_MC) begin
        // Capture the post-MixColumns value in the physical boundary first.
        // The following clock consumes MC_REG, making this a real sequential
        // subround boundary instead of a debug-only observation point.
        PHASE_REG <= PHASE_UPDATE;
      end else if (BUSY_REG && ROUND_REG < 4'd10 && PHASE_REG == PHASE_UPDATE) begin
        STATE_REG <= unpack_semantic_state(MC_REG) ^ NEXT_KEY;
        KEY_REG <= NEXT_KEY;
        if (ROUND_REG == 4'd9) begin
          ROUND_REG <= 4'd10;
          PHASE_REG <= PHASE_FINAL;
        end else begin
          ROUND_REG <= ROUND_REG + 1'b1;
          PHASE_REG <= PHASE_MC;
        end
      end else if (BUSY_REG && ROUND_REG == 4'd10) begin
        STATE_REG <= FINAL_STATE;
        KEY_REG <= NEXT_KEY;
        CIPHERTEXT_REG <= FINAL_STATE;
        ROUND_REG <= 4'h0;
        PHASE_REG <= PHASE_DONE;
        BUSY_REG <= 1'b0;
        DONE_REG <= 1'b1;
      end else if (!BUSY_REG && PHASE_REG == PHASE_DONE) begin
        PHASE_REG <= PHASE_IDLE;
      end
    end
  end

  assign busy = BUSY_REG;
  assign done = DONE_REG;
  assign ciphertext = CIPHERTEXT_REG;
  assign round = ROUND_REG;
  assign phase = PHASE_REG;
endmodule

`default_nettype wire
