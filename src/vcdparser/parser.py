#!/usr/bin/python3
#
import enum
import sys, os
import time
from collections import deque
from time import sleep
from typing import Optional, List, Dict, Deque


class VcdVarType(enum.Enum):
    WIRE = 0
    REGISTER = 1


def parse_type(text: str) -> VcdVarType:
    match text:
        case 'reg':
            return VcdVarType.REGISTER
        case 'wire':
            return VcdVarType.WIRE
    raise TypeError(f"{text} is not a valid VCD variable type")


class VcdVarValue(enum.Enum):
    ZERO = 0
    ONE = 1
    Z = 2
    X = 3


def parse_value(text: str) -> VcdVarValue:
    match text:
        case '0':
            return VcdVarValue.ZERO
        case '1':
            return VcdVarValue.ONE
        case 'x':
            return VcdVarValue.X
        case 'z':
            return VcdVarValue.Z
    raise TypeError(f"{text} is not a valid VCD variable value")


class VcdVariable:
    def __init__(self, type: VcdVarType, size: int, id: str, name: str, bit_ordering: Optional[str]):
        self.type = type
        self.size = size
        self.id = id
        self.name = name
        self.bit_ordering = bit_ordering

    def __str__(self):
        return f"{self.type.name} {self.name} [{self.size}]({self.id}, {self.bit_ordering})"


class VcdScope:
    def __init__(self, context: str, name: str):
        self.context = context
        self.name = name
        self.subscopes: List[VcdScope] = []
        self.variables: Dict[str, VcdVariable] = {}

    def __str__(self):
        return self.format_str()

    def format_str(self, indent: int = 0) -> str:
        prefix = " " * indent
        string = f"{prefix}{self.name} (\n"
        for subscope in self.subscopes:
            string += f"{subscope.format_str(indent + 2)}\n"
        for variable in self.variables.values():
            string += f"{prefix}* {variable}\n"
        string += f"{prefix})"
        return string

    def get_id(self, varname):
        for var in self.variables.values():
            if var.name == varname:
                return var.id

        for subscope in self.subscopes:
            id = subscope.get_id(varname)
            if id is not None:
                return id

        return None


class VcdMetadata:
    def __init__(self):
        self.date: Optional[str] = None
        self.version: Optional[str] = None
        self.timescale: Optional[str] = None
        self.root: VcdScope = VcdScope("", "<ROOT>")

    def __str__(self):
        string = f"Date: {self.date}\n"
        string += f"Version: {self.version}\n"
        string += f"Timescale: {self.timescale}\n"
        string += "\n"
        string += f"{self.root.format_str()}"
        return string


class VcdTimestep:
    def __init__(self, timestamp: int):
        self.timestamp = timestamp
        # self.variables: Dict[str, List[VcdVarValue]] = {}
        self.variables: Dict[str, str] = {}


class Vcd:
    def __init__(self, metadata: VcdMetadata):
        self.metadata = metadata
        self.timesteps: List[VcdTimestep] = []

    def __str__(self):
        string = f"{str(self.metadata)}\n"
        string += f"No. Timesteps: {len(self.timesteps)}"
        return string

    def get_id(self, varname: str) -> str:
        return self.metadata.root.get_id(varname)

    def print_var_changes(self, varname: str):
        id = vcd.get_id(varname)
        for t in vcd.timesteps:
            if id in t.variables:
                print(f"{t.timestamp} - Signal for {varname} changed to {t.variables[id]}")

def parse_vcd_file(filename: str, filter_var_names: Optional[List[str]] = None) -> Vcd:
    line_no = 0
    try:
        with (open(filename, "rt", buffering=1) as vcd_file):
            metadata = VcdMetadata()
            vcd = Vcd(metadata)

            var_lengths = {}
            var_ids = None

            headersection = True
            current_timestep: VcdTimestep = VcdTimestep(-1)
            scope_stack: Deque[VcdScope] = deque()
            scope_stack.append(metadata.root)

            while line := vcd_file.readline():
                line = line[:-1]  # exclude newline.
                line_no += 1
                if line[0] == '#':
                    if headersection:
                        headersection = False
                        if filter_var_names is not None:
                            var_ids = set()
                            for var_name in filter_var_names:
                                var_ids.add(vcd.get_id(var_name))

                    previous_timestep = current_timestep
                    current_timestep = VcdTimestep(int(line[1:].strip()))
                    # Uncomment this line to have the full value range in each timestep
                    # current_timestep.variables = previous_timestep.variables.copy()
                    vcd.timesteps.append(current_timestep)
                    continue
                if len(line) == 0:
                    continue

                if headersection:
                    if line.startswith("$date"):
                        metadata.date, read_lines = read_text_until_end_marker(line, vcd_file)
                        metadata.date = metadata.date[5:-4].strip()
                        if metadata.date.strip() == "unknown":
                            metadata.date = None
                        continue

                    if line.startswith("$version"):
                        metadata.version, read_lines = read_text_until_end_marker(line, vcd_file)
                        metadata.version = metadata.version[8:-4].strip()
                        if metadata.version.strip() == "unknown":
                            metadata.version = None
                        continue

                    if line.startswith("$timescale"):
                        metadata.timescale, read_lines = read_text_until_end_marker(line, vcd_file)
                        metadata.timescale = metadata.timescale[10:-4].strip()
                        if metadata.timescale.strip() == "unknown":
                            vcd.timescale = None
                        continue

                    if line.startswith("$scope"):
                        scopetext, read_lines = read_text_until_end_marker(line, vcd_file)
                        line_no += read_lines
                        parts = scopetext[6:-4].strip().split(" ")
                        if len(parts) < 2:
                            raise RuntimeError(f"Invalid scope: {scopetext}")
                        scope = VcdScope(parts[0], parts[1])
                        scope_stack[len(scope_stack) - 1].subscopes.append(scope)
                        scope_stack.append(scope)

                    if line.startswith("$upscope"):
                        scope_stack.pop()

                    if line.startswith("$var"):
                        vartext, read_lines = read_text_until_end_marker(line, vcd_file)
                        line_no += read_lines
                        parts = vartext[4:-4].strip().split(" ")
                        if len(parts) < 4:
                            raise RuntimeError(f"Invalid scope: {scopetext}")

                        if len(parts) >= 5:
                            ordering = parts[4]
                        else:
                            ordering = None

                        variable = VcdVariable(
                            parse_type(parts[0]),
                            int(parts[1]),
                            parts[2],
                            parts[3],
                            ordering,
                        )

                        scope_stack[len(scope_stack) - 1].variables[variable.id] = variable
                        var_lengths[variable.id] = variable.size

                    if line.startswith("$dumpvars"):
                        current_timestep = VcdTimestep(0) # Initial timestep
                        vcd.timesteps.append(current_timestep)
                        while line := vcd_file.readline():
                            line_no += 1
                            if "$end" in line:
                                break
                            line = line[:-1]
                            id = line[-1]
                            if var_ids is not None and id not in var_ids:
                                continue
                            if id not in var_lengths:
                                continue
                            elif var_lengths[id] > 1:
                                # current_timestep.variables[id] = list(map(parse_value, list(line[1:var_lengths[id]])))
                                current_timestep.variables[id] = line[1:var_lengths[id]]
                            else:
                                # current_timestep.variables[id] = [parse_value(line[0])]
                                current_timestep.variables[id] = line[0]


                else:
                    id = line[-1]
                    if id not in var_lengths:
                        continue
                    if var_ids is not None and id not in var_ids:
                        continue
                    elif var_lengths[id] > 1:
                        # current_timestep.variables[id] = list(map(parse_value, list(line[1:var_lengths[id]])))
                        current_timestep.variables[id] = line[1:var_lengths[id]]
                    else:
                        # current_timestep.variables[id] = [parse_value(line[0])]
                        current_timestep.variables[id] = line[0]
    except Exception as ex:
        raise Exception(f"Error parsing VCD file {filename} in line {line_no}") from ex
    return vcd


def read_text_until_end_marker(line, vcd_file):
    read_lines = 0
    if "$end" in line:
        vartext = line.strip()
    else:
        vartext = line + " "
        while line := vcd_file.readline():
            line = line[:-1]  # exclude newline.
            read_lines += 1
            if "$end" in line:
                vartext += line
                break
            vartext += line + " "
        vartext.strip()
    return vartext, read_lines


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 script.py <filename>')
        sys.exit(1)

    filename = sys.argv[1]
    before = time.monotonic_ns()
    vcd = parse_vcd_file(filename, ["ACT_n"])
    after = time.monotonic_ns()
    print(f"Start parsing VCD file {before}")
    print(f"Finish parsing VCD file {after}")
    print(vcd)
    print(f"Duration: {after - before} ns")

    sleep(10)
    #vcd.print_var_changes("ACT_n")
