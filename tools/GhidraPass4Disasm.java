// Pass 4 companion: dump the full disassembly listing. This engine passes
// animation ids, sprite indices and draw coordinates in registers (SI, AX,
// EBX, EDI), which the decompiler drops; the raw listing preserves them.
// Output path is the script's first argument.
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;

import java.io.PrintWriter;

public class GhidraPass4Disasm extends GhidraScript {
    @Override
    public void run() throws Exception {
        String outputPath = getScriptArgs()[0];
        Listing listing = currentProgram.getListing();
        FunctionManager functionManager = currentProgram.getFunctionManager();
        try (PrintWriter out = new PrintWriter(outputPath, "UTF-8")) {
            for (Instruction instruction : listing.getInstructions(true)) {
                Function function = functionManager.getFunctionAt(instruction.getAddress());
                if (function != null) out.println("\n;=== " + function.getName());
                out.println(instruction.getAddress() + "  " + instruction);
            }
        }
    }
}
