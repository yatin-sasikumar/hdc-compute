
module hdc_compute #(parameter int D=1024)(
    input logic clk,
    input logic rst,
    input logic [D-1:0] quer_vect,
    input logic [D-1:0] class_vect,
    input logic ip_valid,

    output logic op_valid,
    output logic [10:0]  hamm_dist
);    
    logic [D-1:0] xor_reg;
    logic valid_reg;
  
    logic [$clog2(D):0] popcount_comb;


    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            xor_reg <='0;
            valid_reg <=1'b0;
        end else begin
            valid_reg <= ip_valid;
            if (ip_valid)
                xor_reg <= quer_vect^class_vect;
        end
    end

     popcount1024 u_popcount (
        .clk(clk),
        .rst(rst),
        .in_valid(valid_reg),
        .bits_in(xor_reg),
        .count(hamm_dist),
        .out_valid(op_valid));

endmodule
