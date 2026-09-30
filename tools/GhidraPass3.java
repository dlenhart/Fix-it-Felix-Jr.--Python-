// Third pass: decompile callback functions containing LAB_ addresses
// Targets movement speed, stun duration, difficulty scaling, brick throw timing
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;

import java.util.*;

public class GhidraPass3 extends GhidraScript {

    private DecompInterface decomp;

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        decomp.setSimplificationStyle("decompile");

        FunctionManager funcManager = currentProgram.getFunctionManager();
        AddressFactory af = currentProgram.getAddressFactory();

        String[][] targets = {
            {"0040b5e0", "Felix state 0 update — idle behavior, input processing"},
            {"0040b8e0", "Felix state 1 update — walk speed, animation timing"},
            {"0040b9f0", "Felix state 3 update — walk (other direction)"},
            {"0040bd90", "Felix state 4 update — MOVEMENT SPEED, jump trajectory"},
            {"0040bea0", "Felix state 5 update — HAMMER TIMING"},
            {"0040c050", "Felix state 7 update — fall speed"},
            {"0040bc80", "Felix state 8 update — STUN DURATION"},
            {"0040c0d0", "Felix states 6/9 update — hammer extended / dying"},
            {"00402ab0", "Level setup dispatcher — DIFFICULTY SCALING, section type per level"},
            {"00402780", "Level config — DIFFICULTY CURVE PARAMETERS"},
            {"00413de0", "Timer callback — game tick handler, BRICK THROW LOGIC, Controls.log"},
            {"00407940", "Title screen update — attract mode behavior"},
            {"00407990", "Title screen draw"},
        };

        Set<String> decompiled = new HashSet<>();

        for (String[] target : targets) {
            if (monitor.isCancelled()) break;

            String addrStr = target[0];
            String description = target[1];
            Address addr = af.getAddress("0x" + addrStr);

            println("\n\n========================================");
            println("TARGET: LAB_" + addrStr + " / FUN_" + addrStr);
            println("PURPOSE: " + description);
            println("========================================\n");

            Function func = funcManager.getFunctionContaining(addr);

            if (func == null) {
                func = funcManager.getFunctionAt(addr);
            }

            if (func == null) {
                println("[NO FUNCTION FOUND containing or at 0x" + addrStr + "]");
                println("Attempting to look up nearby functions...");
                FunctionIterator iter = funcManager.getFunctions(addr, true);
                if (iter.hasNext()) {
                    Function nearby = iter.next();
                    println("Next function after target: " + nearby.getName() + " at " + nearby.getEntryPoint());
                }
                iter = funcManager.getFunctions(addr, false);
                if (iter.hasNext()) {
                    Function nearby = iter.next();
                    println("Prev function before target: " + nearby.getName() + " at " + nearby.getEntryPoint());
                }
                continue;
            }

            String funcKey = func.getEntryPoint().toString();
            if (decompiled.contains(funcKey)) {
                println("[Already decompiled " + func.getName() + " at " + funcKey + " — skipping duplicate]");
                continue;
            }
            decompiled.add(funcKey);

            println("CONTAINING FUNCTION: " + func.getName() + " at " + func.getEntryPoint());
            println("SIZE: " + func.getBody().getNumAddresses() + " bytes");
            println("---\n");

            decompileFull(func);
        }

        println("\n\n========================================");
        println("FLOATING POINT GLOBALS SCAN");
        println("========================================\n");

        // Known float/double globals that likely hold speed/timing values
        String[] floatAddrs = {
            "00416c00", "00416c04", "00416c08", "00416c0c",
            "00416c10", "00416c14", "00416c18", "00416c1c",
            "00416c20", "00416c24", "00416c28", "00416c2c",
            "00416c30", "00416c34", "00416c38", "00416c3c",
            "00416c40", "00416c44", "00416c48", "00416c4c",
            "00416c50", "00416c54", "00416c58", "00416c5c",
            "00416c60", "00416c64", "00416c68", "00416c6c",
            "00416c70", "00416c74", "00416c78", "00416c7c",
            "00418060", "00418064", "00418068", "0041806c",
            "00418070", "00418074", "00418078", "0041807c",
        };

        for (String addrStr : floatAddrs) {
            try {
                Address addr = af.getAddress("0x" + addrStr);
                byte[] bytes = new byte[4];
                currentProgram.getMemory().getBytes(addr, bytes);
                int intVal = (bytes[0] & 0xFF) | ((bytes[1] & 0xFF) << 8) |
                             ((bytes[2] & 0xFF) << 16) | ((bytes[3] & 0xFF) << 24);
                float floatVal = Float.intBitsToFloat(intVal);
                println("DAT_" + addrStr + " = int:" + intVal + " (0x" + Integer.toHexString(intVal) +
                        ") float:" + floatVal);
            } catch (Exception e) {
                println("DAT_" + addrStr + " = [error: " + e.getMessage() + "]");
            }
        }

        println("\n\n========================================");
        println("ADDITIONAL DATA: PLAYER STATE OFFSETS");
        println("========================================\n");

        // Scan player state block for timing-related constants
        String[] playerDataAddrs = {
            "00424240", "00424244", "00424248", "0042424c",
            "00424250", "00424254", "00424258", "0042425c",
            "00424260", "00424264", "00424268", "0042426c",
            "00424270", "00424274", "00424278", "0042427c",
            "00424280", "00424284", "00424288", "0042428c",
            "00424290", "00424294", "00424298", "0042429c",
            "004242a0", "004242a4", "004242a8", "004242ac",
            "004242b0", "004242b4", "004242b8", "004242bc",
        };

        for (String addrStr : playerDataAddrs) {
            try {
                Address addr = af.getAddress("0x" + addrStr);
                byte[] bytes = new byte[4];
                currentProgram.getMemory().getBytes(addr, bytes);
                int val = (bytes[0] & 0xFF) | ((bytes[1] & 0xFF) << 8) |
                          ((bytes[2] & 0xFF) << 16) | ((bytes[3] & 0xFF) << 24);
                float floatVal = Float.intBitsToFloat(val);
                String extra = "";
                if (floatVal > 0.001f && floatVal < 10000f) {
                    extra = " plausible_float:" + floatVal;
                }
                println("DAT_" + addrStr + " = " + val + " (0x" + Integer.toHexString(val) + ")" + extra);
            } catch (Exception e) {
                println("DAT_" + addrStr + " = [error: " + e.getMessage() + "]");
            }
        }

        decomp.dispose();
        println("\nPASS 3 COMPLETE.");
    }

    private void decompileFull(Function func) {
        DecompileResults results = decomp.decompileFunction(func, 180, monitor);
        if (results != null && results.decompileCompleted()) {
            DecompiledFunction df = results.getDecompiledFunction();
            if (df != null) {
                String code = df.getC();
                for (String line : code.split("\n")) {
                    println(line);
                }
            } else {
                println("[decompilation returned null]");
            }
        } else {
            println("[decompilation failed]");
            if (results != null) {
                println("Error: " + results.getErrorMessage());
            }
        }
    }
}
