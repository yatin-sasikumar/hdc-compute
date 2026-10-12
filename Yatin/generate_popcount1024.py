import math

# Set the input hypervector dimension here, then rerun this script.
N = 1024

if N < 1:
    raise ValueError("N must be >= 1")

# Exact number of bits required to represent every count from 0 through N.
OUT_WIDTH = math.ceil(math.log2(N + 1))

# Each column contains signals with the same binary weight.
# The list grows as carries create new columns; no guessed WIDTH is needed.
columns = [[]]
declarations = []
instances = []
serial = 0

for i in range(N):
    columns[0].append(f"bits_in[{i}]")

# Reduce each column to at most two bits using compressor42 instances.
# compressor42 with cin=0 obeys:
# x1+x2+x3+x4 = sum + 2*carry + 2*cout
k = 0
while k < len(columns):
    while len(columns[k]) > 2:
        group = [
            columns[k].pop(0)
            for _ in range(min(4, len(columns[k])))
        ]
        while len(group) < 4:
            group.append("1'b0")

        sum_sig = f"s_{serial}"
        carry_sig = f"c_{serial}"
        cout_sig = f"co_{serial}"

        declarations.extend([
            f"logic {sum_sig};",
            f"logic {carry_sig};",
            f"logic {cout_sig};",
        ])

        instances.append(
            f"compressor42 u_{serial} ("
            f".x1({group[0]}), .x2({group[1]}), "
            f".x3({group[2]}), .x4({group[3]}), "
            f".cin(1'b0), .sum({sum_sig}), "
            f".carry({carry_sig}), .cout({cout_sig}));"
        )

        # Sum remains at weight 2^k. Both carry outputs have weight 2^(k+1).
        columns[k].append(sum_sig)
        if k + 1 == len(columns):
            columns.append([])
        columns[k + 1].extend([carry_sig, cout_sig])
        serial += 1

    k += 1

# Two-row reduction result. Include enough columns for all generated carries.
HEAP_WIDTH = max(len(columns), OUT_WIDTH)
while len(columns) < HEAP_WIDTH:
    columns.append([])

final = [
    f"logic [{HEAP_WIDTH-1}:0] row_a;",
    f"logic [{HEAP_WIDTH-1}:0] row_b;",
    f"logic [{HEAP_WIDTH}:0] final_sum;",
    f"logic [{OUT_WIDTH-1}:0] count_comb;",
]

for bit in range(HEAP_WIDTH):
    a = columns[bit][0] if len(columns[bit]) >= 1 else "1'b0"
    b = columns[bit][1] if len(columns[bit]) >= 2 else "1'b0"
    final.append(f"assign row_a[{bit}] = {a};")
    final.append(f"assign row_b[{bit}] = {b};")

# Deliberately use '+' here so synthesis can choose how to implement the adder.
final.append(
    f"assign final_sum = {{1'b0, row_a}} + {{1'b0, row_b}};"
)
final.append(f"assign count_comb = final_sum[{OUT_WIDTH-1}:0];")

rtl = [
    "module popcount1024 #(",
    f"    parameter int N = {N},",
    f"    parameter int COUNT_WIDTH = {OUT_WIDTH}",
    ") (",
    "    input  logic                    clk,",
    "    input  logic                    rst,",
    "    input  logic                    in_valid,",
    "    input  logic [N-1:0]            bits_in,",
    "    output logic [COUNT_WIDTH-1:0]  count,",
    "    output logic                    out_valid",
    ");",
    "",
    "    // This generated compressor network is specialized for the N value",
    "    // used by this Python script. Rerun the generator to change N.",
    *declarations,
    "",
    *instances,
    "",
    *final,
    "",
    "    // Registered output with asynchronous active-high reset.",
    "    always_ff @(posedge clk or posedge rst) begin",
    "        if (rst) begin",
    "            count     <= '0;",
    "            out_valid <= 1'b0;",
    "        end else begin",
    "            out_valid <= in_valid;",
    "            if (in_valid)",
    "                count <= count_comb;",
    "        end",
    "    end",
    "",
    "endmodule",
    "",
]

with open("popcount1024.sv", "w", encoding="utf-8") as f:
    f.write("\n".join(rtl))

print(f"Generated popcount1024.sv for N={N}.")
print(f"Exact count width: {OUT_WIDTH} bits.")
print(f"Internal bit-heap / final-adder width: {HEAP_WIDTH} bits.")
print(f"Generated compressor42 instances: {serial}.")
print("Final adder uses '+' so synthesis can map/optimize it.")
print("Sequential reset, count register, and out_valid are included.")
