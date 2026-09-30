// Ghidra headless script to extract game constants from FixitFelixJr.exe
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.data.*;
import ghidra.program.util.*;
import ghidra.app.decompiler.*;

import java.util.*;

public class GhidraExtract extends GhidraScript {

    private DecompInterface decomp;

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        println("================================================================================");
        println("FIX-IT FELIX JR. BINARY ANALYSIS");
        println("================================================================================");

        findInterestingStrings();
        findTimerCalls();
        findLargestFunctions();

        decomp.dispose();
        println("\nDONE.");
    }

    private void findInterestingStrings() throws Exception {
        println("\n\n=== STRING REFERENCES AND DECOMPILED CODE ===\n");

        String[] patterns = {
            "LEVEL", "BONUS LIFE", "FIX WINDOW", "WINDOW", "GAME OVER",
            "BECOME SUPER", "COLLECT PIE", "SCORE", "HIGH SCORE",
            "PRESS JUMP", "FIX LAST", "Controls", "controls",
            "sound", "felix", "texture", "I CAN FIX", "YOU FIXED",
            "Save Game", "Scores", "JUMP OVER", "Game"
        };

        Listing listing = currentProgram.getListing();
        ReferenceManager refManager = currentProgram.getReferenceManager();
        FunctionManager funcManager = currentProgram.getFunctionManager();

        Set<Address> decompiled = new HashSet<>();

        DataIterator dataIter = listing.getDefinedData(true);
        while (dataIter.hasNext() && !monitor.isCancelled()) {
            Data data = dataIter.next();
            if (!data.hasStringValue()) continue;

            String value = data.getValue().toString();
            boolean interesting = false;
            for (String p : patterns) {
                if (value.toLowerCase().contains(p.toLowerCase())) {
                    interesting = true;
                    break;
                }
            }
            if (!interesting) continue;

            Address addr = data.getAddress();
            println("STRING: \"" + value + "\" at " + addr);

            ReferenceIterator refs = refManager.getReferencesTo(addr);
            while (refs.hasNext()) {
                Reference ref = refs.next();
                Address fromAddr = ref.getFromAddress();
                Function func = funcManager.getFunctionContaining(fromAddr);
                if (func != null && !decompiled.contains(func.getEntryPoint())) {
                    decompiled.add(func.getEntryPoint());
                    println("  Referenced from: " + fromAddr + " in function " +
                            func.getName() + " at " + func.getEntryPoint());
                    decompileAndPrint(func);
                } else if (func == null) {
                    println("  Referenced from: " + fromAddr + " (no function)");
                }
            }
            println("");
        }
    }

    private void findTimerCalls() throws Exception {
        println("\n\n=== TIMER AND TIMING ANALYSIS ===\n");

        String[] timerFuncs = {"SetTimer", "KillTimer", "timeGetTime", "GetTickCount"};
        SymbolTable symTable = currentProgram.getSymbolTable();
        ReferenceManager refManager = currentProgram.getReferenceManager();
        FunctionManager funcManager = currentProgram.getFunctionManager();

        for (String funcName : timerFuncs) {
            SymbolIterator symbols = symTable.getSymbols(funcName);
            while (symbols.hasNext()) {
                Symbol sym = symbols.next();
                ReferenceIterator timerRefs = refManager.getReferencesTo(sym.getAddress());
                while (timerRefs.hasNext()) {
                    Reference ref = timerRefs.next();
                    Function caller = funcManager.getFunctionContaining(ref.getFromAddress());
                    if (caller != null) {
                        println(funcName + "() called from " + ref.getFromAddress() +
                                " in function " + caller.getName());
                        decompileAndPrint(caller);
                    }
                }
            }
        }
    }

    private void findLargestFunctions() throws Exception {
        println("\n\n=== LARGEST FUNCTIONS (likely game logic) ===\n");

        FunctionManager funcManager = currentProgram.getFunctionManager();
        List<Object[]> funcs = new ArrayList<>();

        FunctionIterator iter = funcManager.getFunctions(true);
        while (iter.hasNext()) {
            Function func = iter.next();
            long size = func.getBody().getNumAddresses();
            funcs.add(new Object[]{size, func.getName(), func.getEntryPoint()});
        }

        funcs.sort((a, b) -> Long.compare((Long)b[0], (Long)a[0]));

        for (int i = 0; i < Math.min(30, funcs.size()); i++) {
            Object[] f = funcs.get(i);
            println("  " + f[0] + " bytes: " + f[1] + " at " + f[2]);
        }

        // Decompile top 10 largest (most likely game logic)
        println("\n\n=== DECOMPILED LARGEST FUNCTIONS ===\n");
        Set<Address> done = new HashSet<>();
        for (int i = 0; i < Math.min(10, funcs.size()); i++) {
            if (monitor.isCancelled()) break;
            Address addr = (Address) funcs.get(i)[2];
            if (done.contains(addr)) continue;
            done.add(addr);
            Function func = funcManager.getFunctionAt(addr);
            if (func != null) {
                println("=== FUNCTION: " + func.getName() + " (" + funcs.get(i)[0] + " bytes) ===");
                decompileAndPrint(func);
                println("");
            }
        }
    }

    private void decompileAndPrint(Function func) {
        DecompileResults results = decomp.decompileFunction(func, 60, monitor);
        if (results != null && results.decompileCompleted()) {
            DecompiledFunction df = results.getDecompiledFunction();
            if (df != null) {
                String code = df.getC();
                String[] lines = code.split("\n");
                println("  --- Decompiled (" + lines.length + " lines) ---");
                int maxLines = Math.min(lines.length, 120);
                for (int i = 0; i < maxLines; i++) {
                    println("    " + lines[i]);
                }
                if (lines.length > maxLines) {
                    println("    ... (" + (lines.length - maxLines) + " more lines)");
                }
                println("  --- End ---");
            }
        }
    }
}
