`default_nettype none

module aes_sbox_byte(
  input  wire [7:0] in_byte,
  output wire [7:0] out_byte
);
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

  function automatic [7:0] aes_sbox;
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
      aes_sbox = inverse ^ rotl8(inverse, 1) ^ rotl8(inverse, 2) ^
                 rotl8(inverse, 3) ^ rotl8(inverse, 4) ^ 8'h63;
    end
  endfunction

  assign out_byte = aes_sbox(in_byte);
endmodule

`default_nettype wire
