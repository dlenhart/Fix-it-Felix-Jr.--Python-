# Ghidra headless script to extract game constants from FixitFelixJr.exe
# Run via: analyzeHeadless <project_dir> <project_name> -import <exe> -postScript ghidra_extract.py
#
# This script finds string references and traces back to surrounding code
# to extract numeric constants (timing, scoring, grid dimensions, difficulty).

from ghidra.program.model.listing import CodeUnit
from ghidra.program.util import DefinedDataIterator
from ghidra.app.decompiler import DecompInterface
import ghidra.program.model.symbol.SourceType as SourceType

program = currentProgram
listing = program.getListing()
memory = program.getMemory()
refManager = program.getReferenceManager()
funcManager = program.getFunctionManager()

# Set up decompiler
decomp = DecompInterface()
decomp.openProgram(program)

INTERESTING_STRINGS = [
    "LEVEL", "BONUS LIFE", "FIX WINDOW", "WINDOW", "GAME OVER",
    "BECOME SUPER", "COLLECT PIE", "SCORE", "HIGH SCORE",
    "PRESS JUMP", "FIX LAST", "Controls.log", "SetTimer",
    "sound", "felix", "texture", "I CAN FIX IT",
]

print("=" * 80)
print("FIX-IT FELIX JR. BINARY ANALYSIS")
print("=" * 80)

# 1. Find all defined strings and their cross-references
print("\n\n=== STRING REFERENCES AND SURROUNDING CODE ===\n")

for data in DefinedDataIterator.definedStrings(program):
    value = data.getValue()
    if not isinstance(value, (str,)):
        try:
            value = str(value)
        except:
            continue

    is_interesting = any(s.lower() in value.lower() for s in INTERESTING_STRINGS)
    if not is_interesting:
        continue

    addr = data.getAddress()
    refs = refManager.getReferencesTo(addr)
    ref_list = []
    for ref in refs:
        ref_list.append(ref)

    if not ref_list:
        print("STRING: \"{}\" at {} (no xrefs)".format(value, addr))
        continue

    print("STRING: \"{}\" at {}".format(value, addr))

    for ref in ref_list:
        from_addr = ref.getFromAddress()
        func = funcManager.getFunctionContaining(from_addr)
        if func:
            print("  Referenced from: {} in function {} at {}".format(
                from_addr, func.getName(), func.getEntryPoint()))

            # Decompile the function
            results = decomp.decompileFunction(func, 30, monitor)
            if results and results.decompileCompleted():
                decomp_func = results.getDecompiledFunction()
                if decomp_func:
                    c_code = decomp_func.getC()
                    # Print the decompiled code (truncated)
                    lines = c_code.split('\n')
                    print("  --- Decompiled ({} lines) ---".format(len(lines)))
                    for line in lines[:80]:
                        print("    " + line)
                    if len(lines) > 80:
                        print("    ... ({} more lines)".format(len(lines) - 80))
                    print("  --- End decompiled ---")
        else:
            print("  Referenced from: {} (no function)".format(from_addr))

    print("")

# 2. Find SetTimer and KillTimer calls for timing constants
print("\n\n=== TIMER CALLS (SetTimer/KillTimer) ===\n")

for func_name in ["SetTimer", "KillTimer"]:
    func = None
    for f in funcManager.getFunctions(True):
        if f.getName() == func_name:
            func = f
            break

    if not func:
        # Try to find it as an external/thunk
        symbol_table = program.getSymbolTable()
        symbols = symbol_table.getSymbols(func_name)
        for sym in symbols:
            refs = refManager.getReferencesTo(sym.getAddress())
            for ref in refs:
                from_addr = ref.getFromAddress()
                caller = funcManager.getFunctionContaining(from_addr)
                if caller:
                    print("{}() called from {} in function {}".format(
                        func_name, from_addr, caller.getName()))
                    results = decomp.decompileFunction(caller, 30, monitor)
                    if results and results.decompileCompleted():
                        decomp_func = results.getDecompiledFunction()
                        if decomp_func:
                            c_code = decomp_func.getC()
                            lines = c_code.split('\n')
                            # Find lines near the timer call
                            for i, line in enumerate(lines):
                                if func_name in line or "timer" in line.lower():
                                    start = max(0, i - 3)
                                    end = min(len(lines), i + 4)
                                    for j in range(start, end):
                                        marker = ">>>" if j == i else "   "
                                        print("  {} {}".format(marker, lines[j]))
                    print("")

# 3. Find float and integer constants in key functions
print("\n\n=== KEY FUNCTION ANALYSIS ===\n")

analyzed_funcs = set()
for data in DefinedDataIterator.definedStrings(program):
    value = data.getValue()
    if not isinstance(value, (str,)):
        try:
            value = str(value)
        except:
            continue

    key_patterns = ["LEVEL", "BONUS", "SUPER", "FIX WINDOW", "Controls"]
    if not any(p.lower() in str(value).lower() for p in key_patterns):
        continue

    addr = data.getAddress()
    refs = refManager.getReferencesTo(addr)
    for ref in refs:
        func = funcManager.getFunctionContaining(ref.getFromAddress())
        if func and func.getEntryPoint() not in analyzed_funcs:
            analyzed_funcs.add(func.getEntryPoint())
            print("FUNCTION: {} at {} (refs string \"{}\")".format(
                func.getName(), func.getEntryPoint(), value))

            # Full decompilation
            results = decomp.decompileFunction(func, 60, monitor)
            if results and results.decompileCompleted():
                decomp_func = results.getDecompiledFunction()
                if decomp_func:
                    c_code = decomp_func.getC()
                    print(c_code)
            print("\n" + "=" * 60 + "\n")

# 4. Look for the Controls.log file loading function
print("\n\n=== CONTROLS.LOG PARSING ===\n")

for data in DefinedDataIterator.definedStrings(program):
    value = data.getValue()
    try:
        value = str(value)
    except:
        continue
    if "control" in value.lower() or "Controls" in value:
        addr = data.getAddress()
        refs = refManager.getReferencesTo(addr)
        for ref in refs:
            func = funcManager.getFunctionContaining(ref.getFromAddress())
            if func:
                print("Controls-related function: {} at {}".format(
                    func.getName(), func.getEntryPoint()))
                results = decomp.decompileFunction(func, 60, monitor)
                if results and results.decompileCompleted():
                    decomp_func = results.getDecompiledFunction()
                    if decomp_func:
                        print(decomp_func.getC())
                print("\n" + "-" * 40 + "\n")

# 5. Dump all functions with their sizes (to find main game loop)
print("\n\n=== LARGEST FUNCTIONS (likely game logic) ===\n")

func_sizes = []
for func in funcManager.getFunctions(True):
    body = func.getBody()
    size = body.getNumAddresses()
    func_sizes.append((size, func.getName(), func.getEntryPoint()))

func_sizes.sort(reverse=True)
for size, name, addr in func_sizes[:30]:
    print("  {} bytes: {} at {}".format(size, name, addr))

decomp.dispose()
print("\n\nDONE.")
