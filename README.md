# vcdparser

A simple VCD parser to access the contents of a VCD file in python.

The goal is to provide an easy to use, lightweight parser for VCD files.
The parser also aims to be quite fast (for a python library 😉).

## What does it do?

This library contains a simple parser, which reads in VCD files and provides you with the raw data from this file.

## How to use

To install the latest version from PyPI use `pip install vcdparser`.
After that you can import the parser using `import vcdparser.parser`.

This is a simple script showing you how to parse a file and get the first 10 changes of a signal named `"CLK"`:

````python
import vcdparser.parser

vcd = parser.parse_vcd_file("your_file_path.vcd")
clk_id = vcd.get_id("CLK")

count = 0
for t in vcd.timesteps:
    if clk_id in t.variables:
        count += 1
        print(f"CLK changed to {t.variables[clk_id]}")
        if count >= 10:
            break
````

## Contributing

We are always happy to receive contributions!
Please take a look at [the contribution guidelines](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md) before making changes.
