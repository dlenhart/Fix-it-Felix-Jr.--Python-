// Deep extraction of game logic functions - no line limit
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.data.*;
import ghidra.program.util.*;
import ghidra.app.decompiler.*;

import java.util.*;

public class GhidraDeep extends GhidraScript {

    private DecompInterface decomp;

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        decomp.setSimplificationStyle("decompile");

        FunctionManager funcManager = currentProgram.getFunctionManager();

        // Decompile specific key functions with NO line limit
        String[] targets = {
            "FUN_0040a210",  // Largest function (3407 bytes) - game init
            "FUN_00402e00",  // 2nd largest (2544 bytes) - level setup
            "FUN_00405550",  // 3rd largest (1842 bytes)
            "FUN_00414040",  // WndProc with SetTimer (1647 bytes)
            "FUN_0040c3d0",  // 5th largest (1529 bytes)
            "FUN_0040fa30",  // 6th largest (1493 bytes)
            "FUN_00410bf0",  // 7th largest (1446 bytes)
            "FUN_0040e6d0",  // 8th largest (1393 bytes) - refs "felix%d"
            "FUN_00404ea0",  // 9th largest (1292 bytes)
            "FUN_00404500",  // Level display function
            "FUN_00408280",  // High score display - has TIME LEFT, score format
            "FUN_00408760",  // Game over handler
            "FUN_00413680",  // Controls.log + command line parser
            "FUN_00413950",  // Score/save related
            "FUN_00408fc0",  // Near instruction strings
            "FUN_0040f820",  // refs "sound%d"
            "FUN_00411e90",  // refs "texture2"
            "FUN_004131e0",  // Save game
            "FUN_004132d0",  // Load save
            "FUN_00407d50",  // High scores display
            "FUN_00407f50",  // Network controls polling
        };

        for (String name : targets) {
            if (monitor.isCancelled()) break;
            FunctionIterator iter = funcManager.getFunctions(true);
            while (iter.hasNext()) {
                Function func = iter.next();
                if (func.getName().equals(name)) {
                    println("\n\n########################################");
                    println("# FUNCTION: " + name + " (" + func.getBody().getNumAddresses() + " bytes)");
                    println("########################################\n");
                    decompileFull(func);
                    break;
                }
            }
        }

        // Also dump all global data references that look like constants
        println("\n\n########################################");
        println("# GLOBAL CONSTANTS SCAN");
        println("########################################\n");

        // Look for interesting data at known addresses
        Listing listing = currentProgram.getListing();
        AddressFactory af = currentProgram.getAddressFactory();

        // Scan data section for initialized values
        String[] dataAddrs = {
            "00424240", "0042423c", "00424244", "00424258",
            "00424288", "0042428c", "00424254", "00424250",
            "004243a4", "004243a8", "004243b0", "004243b4",
            "004243c0", "004243c8", "004243cc", "004243d0",
            "004243d4", "004243fc",
            "00420374", "004201e8",
        };

        for (String addrStr : dataAddrs) {
            try {
                Address addr = af.getAddress("0x" + addrStr);
                Data data = listing.getDataAt(addr);
                if (data != null) {
                    println("DAT_" + addrStr + " = " + data.getValue() + " (type: " + data.getDataType().getName() + ")");
                } else {
                    // Try reading raw bytes
                    byte[] bytes = new byte[4];
                    currentProgram.getMemory().getBytes(addr, bytes);
                    int val = (bytes[0] & 0xFF) | ((bytes[1] & 0xFF) << 8) |
                              ((bytes[2] & 0xFF) << 16) | ((bytes[3] & 0xFF) << 24);
                    println("DAT_" + addrStr + " = 0x" + Integer.toHexString(val) + " (" + val + ") [raw]");
                }
            } catch (Exception e) {
                println("DAT_" + addrStr + " = [error: " + e.getMessage() + "]");
            }
        }

        decomp.dispose();
        println("\nDEEP ANALYSIS DONE.");
    }

    private void decompileFull(Function func) {
        DecompileResults results = decomp.decompileFunction(func, 120, monitor);
        if (results != null && results.decompileCompleted()) {
            DecompiledFunction df = results.getDecompiledFunction();
            if (df != null) {
                String code = df.getC();
                // Print ALL lines - no truncation
                for (String line : code.split("\n")) {
                    println(line);
                }
            } else {
                println("[decompilation returned null]");
            }
        } else {
            println("[decompilation failed]");
        }
    }
}
