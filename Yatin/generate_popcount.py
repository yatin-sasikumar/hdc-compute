#!/usr/bin/env python3
"""Generate a parameter-sized compressor-tree popcount RTL.

Usage:
    python generate_popcount.py 1024
    python generate_popcount.py 2048 --output-dir generated
    python generate_popcount.py 256 --module-name popcount256

The generated RTL filename follows the requested dimension:
    popcount1024.sv, popcount2048.sv, etc.

Requires compressor42.sv to be compiled alongside the generated file.
"""

import argparse
import math
from pathlib import Path


def build_rtl(n: int, module_name: str) -> tuple[str, int, int]:
    if n < 1:
        raise ValueError("N must be >= 1")

    count_width = math.ceil(math.log2(n + 1))

    # Each column holds signal names with the same binary weight.
    columns: list[list[str]] = [[]]
    declarations: list[str] = []
    instances: list[str] = []
    serial = 0

    for bit in range(n):
        columns[0].append(f"bits_in[{bit}]")

    # Reduce each column to <= 2 bits using the verified compressor cell.
    # With cin=0: x1+x2+x3+x4 = sum + 2*carry + 2*cout.
    k = 0
    while k < len(columns):
        while len(columns[k]) > 2:
            group = [
                columns[k].pop(0)
                for _ in range(min(4, len(columns[k])))
            ]
            while len(group) < 4:
                group.append("1'b0")

            s = f"s_{serial}"
            c = f"c_{serial}"
            co = f"co_{serial}"

            declarations.extend([
                f"logic {s};",
                f"logic {c};",
                f"logic {co};",
            ])
            instances.append(
                f"compressor42 u_{serial} ("
                f".x1({group[0]}), .x2({group[1]}), "
                f".x3({group[2]}), .x4({group[3]}), "
                f".cin(1'b0), .sum({s}), "
                f".carry({c}), .cout({co}));"
            )

            columns[k].append(s)
            if k + 1 == len(columns):
                columns.append([])
            columns[k + 1].extend([c, co])
            serial += 1
        k += 1

    # The generated heap may have high empty columns; preserve the full
    # represented width for the final addition, then expose count_width bits.
    heap_width = max(len(columns), count_width)
    while len(columns) < heap_width:
        columns.append([])

    final: list[str] = [
        f"logic [{heap_width - 1}:0] row_a;",
        f"logic [{heap_width - 1}:0] row_b;",
        f"logic [{heap_width}:0] final_sum;",
        f"logic [{count_width - 1}:0] count_comb;",
    ]

    for bit in range(heap_width):
        a = columns[bit][0] if len(columns[bit]) > 0 else "1'b0"
        b = columns[bit][1] if len(columns[bit]) > 1 else "1'b0"
        final.extend([
            f"assign row_a[{bit}] = {a};",
            f"assign row_b[{bit}] = {b};",
        ])

    # Intentionally use + so the synthesis tool decides the implementation.
    final.append(
        f"assign final_sum = {{1'b0, row_a}} + {{1'b0, row_b}};"
    )
    final.append(
        f"assign count_comb = final_sum[{count_width - 1}:0];"
    )

    rtl = [
        f"module {module_name} #(",
        f"    parameter int N = {n},",
        f"    parameter int COUNT_WIDTH = {count_width}",
        ") (",
        "    input  logic                    clk,",
        "    input  logic                    rst,",
        "    input  logic                    in_valid,",
        "    input  logic [N-1:0]            bits_in,",
        "    output logic [COUNT_WIDTH-1:0]  count,",
        "    output logic                    out_valid",
        ");",
        "",
        "    // Generated for N={n}; rerun the generator to change dimension.",
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

    # Expand the generated-dimension comment for readability.
    rtl = [line.replace("// Generated for N={n};", f"// Generated for N={n};") for line in rtl]
    return "\n".join(rtl), count_width, serial


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a compressor-based sequential popcount RTL module."
    )
    parser.add_argument(
        "dimension",
        type=int,
        help="number of input bits, e.g. 1024 or 2048",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="directory for generated RTL (default: current directory)",
    )
    parser.add_argument(
        "--module-name",
        default=None,
        help="optional Verilog module name (default: popcount<DIMENSION>)",
    )
    args = parser.parse_args()

    n = args.dimension
    if n < 1:
        parser.error("dimension must be >= 1")

    module_name = args.module_name or f"popcount{n}"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "popcount.sv"

    rtl, count_width, compressor_count = build_rtl(n, module_name)
    output_path.write_text(rtl, encoding="utf-8")

    print(f"Generated: {output_path}")
    print(f"Input dimension: {n}")
    print(f"Exact count width: {count_width} bits")
    print(f"Compressor instances: {compressor_count}")
    print("Final adder uses '+' for synthesis mapping.")
    print("Sequential clk/rst/in_valid/count/out_valid logic included.")


if __name__ == "__main__":
    main()
