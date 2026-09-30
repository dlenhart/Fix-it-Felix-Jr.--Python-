// Pass 3b: force-create functions at LAB_ addresses that auto-analysis missed,
// then decompile them. These are callback targets reached via function pointers.
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;
import ghidra.app.cmd.function.CreateFunctionCmd;

public class GhidraPass3b extends GhidraScript {

    private DecompInterface decomp;

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        decomp.setSimplificationStyle("decompile");

        FunctionManager funcManager = currentProgram.getFunctionManager();
        AddressFactory af = currentProgram.getAddressFactory();

        String[][] targets = {
            {"0040b5e0", "Felix state 0 — idle behavior, input processing"},
            {"0040b8e0", "Felix state 1 — walk speed, animation timing"},
            {"0040b9f0", "Felix state 3 — walk (other direction)"},
            {"0040bd90", "Felix state 4 — MOVEMENT SPEED, jump trajectory"},
            {"0040bc80", "Felix state 8 — STUN DURATION"},
            {"0040c050", "Felix state 7 — fall speed"},
            {"0040c0d0", "Felix states 6/9 — hammer extended / dying"},
            {"00413de0", "Timer callback — BRICK THROW LOGIC, Controls.log"},
            {"00407940", "Title screen update — attract mode"},
            {"00407990", "Title screen draw"},
        };

        for (String[] target : targets) {
            if (monitor.isCancelled()) break;

            String addrStr = target[0];
            String description = target[1];
            Address addr = af.getAddress("0x" + addrStr);

            println("\n\n========================================");
            println("TARGET: 0x" + addrStr);
            println("PURPOSE: " + description);
            println("========================================\n");

            Function func = funcManager.getFunctionAt(addr);
            if (func == null) {
                func = funcManager.getFunctionContaining(addr);
            }

            if (func == null) {
                println("No existing function — creating one at 0x" + addrStr + "...");
                CreateFunctionCmd cmd = new CreateFunctionCmd(addr);
                boolean ok = cmd.applyTo(currentProgram, monitor);
                if (ok) {
                    func = funcManager.getFunctionAt(addr);
                    if (func != null) {
                        println("Created function: " + func.getName() + " (" +
                                func.getBody().getNumAddresses() + " bytes)");
                    }
                } else {
                    println("[CreateFunctionCmd failed at 0x" + addrStr + ": " +
                            cmd.getStatusMsg() + "]");
                }
            }

            if (func == null) {
                println("[STILL NO FUNCTION at 0x" + addrStr + "]");

                println("Disassembling raw bytes at target address...");
                try {
                    byte[] bytes = new byte[128];
                    currentProgram.getMemory().getBytes(addr, bytes);
                    StringBuilder sb = new StringBuilder();
                    for (int i = 0; i < bytes.length; i++) {
                        if (i > 0 && i % 16 == 0) {
                            println("  " + String.format("%08x", addr.getOffset() + i - 16) +
                                    ": " + sb.toString());
                            sb.setLength(0);
                        }
                        sb.append(String.format("%02x ", bytes[i] & 0xFF));
                    }
                    if (sb.length() > 0) {
                        println("  " + String.format("%08x", addr.getOffset() +
                                (bytes.length / 16) * 16) + ": " + sb.toString());
                    }
                } catch (Exception e) {
                    println("[Could not read bytes: " + e.getMessage() + "]");
                }
                continue;
            }

            println("FUNCTION: " + func.getName() + " at " + func.getEntryPoint());
            println("SIZE: " + func.getBody().getNumAddresses() + " bytes");
            println("---\n");

            decompileFull(func);
        }

        // Also decompile the large function FUN_0040b510 which contains most Felix state callbacks
        println("\n\n========================================");
        println("BONUS: FUN_0040b510 (parent of Felix state callbacks)");
        println("========================================\n");

        Address parentAddr = af.getAddress("0x0040b510");
        Function parentFunc = funcManager.getFunctionAt(parentAddr);
        if (parentFunc != null) {
            println("FUNCTION: " + parentFunc.getName() + " at " + parentFunc.getEntryPoint());
            println("SIZE: " + parentFunc.getBody().getNumAddresses() + " bytes");
            println("---\n");
            decompileFull(parentFunc);
        } else {
            println("[FUN_0040b510 not found]");
        }

        // And FUN_004078e0 which is parent of title screen callbacks
        println("\n\n========================================");
        println("BONUS: FUN_004078e0 (parent of title screen callbacks)");
        println("========================================\n");

        Address titleAddr = af.getAddress("0x004078e0");
        Function titleFunc = funcManager.getFunctionAt(titleAddr);
        if (titleFunc != null) {
            println("FUNCTION: " + titleFunc.getName() + " at " + titleFunc.getEntryPoint());
            println("SIZE: " + titleFunc.getBody().getNumAddresses() + " bytes");
            println("---\n");
            decompileFull(titleFunc);
        } else {
            println("[FUN_004078e0 not found]");
        }

        // And FUN_00413950 which is parent of timer/Controls.log callback
        println("\n\n========================================");
        println("BONUS: FUN_00413950 (parent of timer callback)");
        println("========================================\n");

        Address timerAddr = af.getAddress("0x00413950");
        Function timerFunc = funcManager.getFunctionAt(timerAddr);
        if (timerFunc != null) {
            println("FUNCTION: " + timerFunc.getName() + " at " + timerFunc.getEntryPoint());
            println("SIZE: " + timerFunc.getBody().getNumAddresses() + " bytes");
            println("---\n");
            decompileFull(timerFunc);
        } else {
            println("[FUN_00413950 not found]");
        }

        decomp.dispose();
        println("\nPASS 3b COMPLETE.");
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
