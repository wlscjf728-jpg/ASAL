`timescale 1ns/1ps
`default_nettype none

// Functional simulation models for the cells in RTL/config/class_scan.db.
// The Boolean functions were queried from the synthesis library; sequential
// cells model the active-high CD clear and scan-enable mux used by DC.
module AN2(input wire A, B, output wire Z); assign Z = A & B; endmodule
module AN3(input wire A, B, C, output wire Z); assign Z = A & B & C; endmodule
module AO1(input wire A, B, C, D, output wire Z); assign Z = ~((A & B) | C | D); endmodule
module AO2(input wire A, B, C, D, output wire Z); assign Z = ~((A & B) | (C & D)); endmodule
module AO3(input wire A, B, C, D, output wire Z); assign Z = ~((A | B) & C & D); endmodule
module AO4(input wire A, B, C, D, output wire Z); assign Z = ~((A | B) & (C | D)); endmodule
module AO6(input wire A, B, C, output wire Z); assign Z = ~((A & B) | C); endmodule
module AO7(input wire A, B, C, output wire Z); assign Z = ~((A | B) & C); endmodule
module EN(input wire A, B, output wire Z); assign Z = ~(A ^ B); endmodule
module EO(input wire A, B, output wire Z); assign Z = A ^ B; endmodule
module EO1(input wire A, B, C, D, output wire Z); assign Z = ~((A & B) | ~(C | D)); endmodule
module EON1(input wire A, B, C, D, output wire Z); assign Z = ~((A | B) & ~(C & D)); endmodule
module IV(input wire A, output wire Z); assign Z = ~A; endmodule
module IVI(input wire A, output wire Z); assign Z = ~A; endmodule
module MUX21H(input wire A, B, S, output wire Z); assign Z = (~S & A) | (S & B); endmodule
module MUX21L(input wire A, B, S, output wire Z); assign Z = (~S & ~A) | (S & ~B); endmodule
module MUX31L(input wire D0, D1, D2, A, B, output wire Z);
  assign Z = (~D0 & ~A & ~B) | (~D1 & A & ~B) | (~D2 & B);
endmodule
module ND2(input wire A, B, output wire Z); assign Z = ~(A & B); endmodule
module ND2I(input wire A, B, output wire Z); assign Z = ~(A & B); endmodule
module ND3(input wire A, B, C, output wire Z); assign Z = ~(A & B & C); endmodule
module NR2(input wire A, B, output wire Z); assign Z = ~(A | B); endmodule
module NR3(input wire A, B, C, output wire Z); assign Z = ~(A | B | C); endmodule
module NR2I(input wire A, B, output wire Z); assign Z = ~(A | B); endmodule
module ND4(input wire A, B, C, D, output wire Z); assign Z = ~(A & B & C & D); endmodule
module NR4(input wire A, B, C, D, output wire Z); assign Z = ~(A | B | C | D); endmodule
module OR2(input wire A, B, output wire Z); assign Z = A | B; endmodule
module OR2I(input wire A, B, output wire Z); assign Z = A | B; endmodule
module OR3(input wire A, B, C, output wire Z); assign Z = A | B | C; endmodule

module FD2(input wire D, CP, CD, output reg Q, output wire QN);
  initial Q = 1'b0;
  always @(posedge CP or negedge CD) begin
    if (!CD) Q <= 1'b0;
    else Q <= D;
  end
  assign QN = ~Q;
endmodule

module FD2S(input wire D, TI, TE, CP, CD, output reg Q, output wire QN);
  initial Q = 1'b0;
  always @(posedge CP or negedge CD) begin
    if (!CD) Q <= 1'b0;
    else if (TE) Q <= TI;
    else Q <= D;
  end
  assign QN = ~Q;
endmodule

`default_nettype wire
