module compressor42 (
    input  logic x1,
    input  logic x2,
    input  logic x3,
    input  logic x4,
    input  logic cin,

    output logic sum,
    output logic carry,
    output logic cout
);

    logic s1;

    // First full-adder stage
    assign s1   = x1 ^ x2 ^ x3;
    assign cout = (x1 & x2) | (x1 & x3) | (x2 & x3);

    // Second full-adder stage
    assign sum = s1 ^ x4 ^ cin;

    assign carry = (s1 & x4) | (s1 & cin) | (x4 & cin);

endmodule