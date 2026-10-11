
module tb_hdc_compute;

    logic clk = 0;
    logic rst = 1;
    logic [1023:0] quer_vect = '0;
    logic [1023:0] class_vect = '0;
    logic ip_valid = 0;

    logic op_valid;
    logic [10:0] hamm_dist;

    integer errors = 0;
    integer expected;
    integer i, j;

    hdc_compute dut (
        .clk(clk),
        .rst(rst),
        .quer_vect(quer_vect),
        .class_vect(class_vect),
        .ip_valid(ip_valid),
        .op_valid(op_valid),
        .hamm_dist(hamm_dist)
    );

    always #5 clk = ~clk;

    task automatic send_and_check(
        input logic [1023:0] q,
        input logic [1023:0] c,
        input integer exp_dist
    );
        begin
            @(negedge clk);
            quer_vect = q;
            class_vect = c;
            ip_valid = 1'b1;

            @(posedge clk);
            #1;
            @(negedge clk);
            ip_valid = 1'b0;
            // The XOR stage has captured the input.
            if (op_valid !== 1'b0)
                $display("NOTE: op_valid already high; check pipeline alignment");

            @(posedge clk);
            #1;

            if (op_valid !== 1'b1)
                $fatal(1, "op_valid missing");

            if (hamm_dist !== exp_dist[10:0])
                $fatal(1, "Expected %0d, got %0d", exp_dist, hamm_dist);
        end
    endtask

    initial begin
        $dumpfile("hdc_compute.vcd");
        $dumpvars(0, tb_hdc_compute);

        repeat (2) @(negedge clk);
        rst = 0;

        // Identical vectors: distance 0
        send_and_check('0, '0, 0);

        // All bits differ: distance 1024
        send_and_check('0, '1, 1024);

        // Exactly one differing bit
        begin
            logic [1023:0] q, c;
            q = '0;
            c = '0;
            c[37] = 1'b1;
            send_and_check(q, c, 1);
        end

        // Half the bits differ
        begin
            logic [1023:0] q, c;
            q = '0;
            c = '0;
            c[511:0] = '1;
            send_and_check(q, c, 512);
        end

        // Check reset clears outputs
        @(negedge clk);
        ip_valid = 0;
        rst = 1;
        #1;

        if (hamm_dist !== 11'd0 || op_valid !== 1'b0) begin
            $display("FAIL: reset behavior");
            errors = errors + 1;
        end

        repeat (2) @(negedge clk);
        rst = 0;

        if (errors == 0)
            $display("ALL HDC TESTS PASSED");
        else
            $display("HDC TESTS FAILED: %0d errors", errors);

        $finish;
    end

endmodule
