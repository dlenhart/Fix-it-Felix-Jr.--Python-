// Fifth pass: everything needed to decode the intro animation.
//
// Pass 4 decompiled every function, but the intro script passes node and
// animation ids in registers (dropped by the decompiler), creates its sprite
// nodes somewhere unidentified, and advances its step from outside the script
// function. This pass answers those questions with targeted output:
//   1. decompilation + disassembly of the intro script family and helpers
//   2. every read/write of the intro globals, with the instruction
//   3. register context before every call to the node/anim/sound helpers
//   4. raw data: the script pointer table, the 0x419e80 table, the whole
//      animation table with frame lists
//   5. strings referenced from the script family
// Output path is the script's first argument.
// See docs/superpowers/plans/2026-11-13-intro-decode.md.
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.symbol.*;

import java.io.PrintWriter;
import java.util.*;

public class GhidraPass5Intro extends GhidraScript {

    private static final long SCRIPT_FAMILY_START = 0x401000L;
    private static final long SCRIPT_FAMILY_END = 0x402e00L;

    /** Node placement, animation, music and window-damage helpers seen in the intro. */
    private static final long[] HELPER_FUNCTIONS = {
        0x402780L, 0x406050L, 0x409840L, 0x40ec50L, 0x40ecc0L, 0x40ecf0L, 0x40f4a0L,
    };

    /** Calls to these get their preceding instructions printed (register arguments). */
    private static final long[] REGISTER_ARGUMENT_CALLEES = {
        0x40ec50L, 0x40ecc0L, 0x40ecf0L, 0x40f4a0L, 0x409840L,
    };
    private static final int CALL_CONTEXT_INSTRUCTIONS = 10;

    /** Intro state globals: script callbacks, node pointers, coordinates, step, counters. */
    private static final long GLOBALS_START = 0x424340L;
    private static final long GLOBALS_END = 0x424410L;
    private static final long STEP_GLOBAL = 0x4243ecL;
    private static final long STEP_DONE_FLAG = 0x424402L;

    /** Other globals the intro touches whose meaning is still open. */
    private static final long[] EXTRA_GLOBALS = { 0x41a248L, 0x41a298L, 0x42427cL };

    private static final long SCRIPT_POINTER_TABLE = 0x402dd0L;
    private static final int SCRIPT_POINTER_TABLE_ENTRIES = 16;
    private static final long INTRO_CYCLE_TABLE = 0x419e80L;
    private static final int INTRO_CYCLE_TABLE_ENTRIES = 8;

    /** Animation defs: 12 bytes [u16 id, u16 frame_count][i32 mode][ptr frame_list]. */
    private static final long ANIMATION_TABLE = 0x419800L;
    private static final int ANIMATION_DEF_SIZE = 12;
    private static final int ANIMATION_FRAME_SIZE = 10;
    private static final int ANIMATION_TABLE_MAX_ENTRIES = 256;

    private Memory memory;
    private Listing listing;
    private FunctionManager functionManager;
    private ReferenceManager referenceManager;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("usage: GhidraPass5Intro <output path>");
        memory = currentProgram.getMemory();
        listing = currentProgram.getListing();
        functionManager = currentProgram.getFunctionManager();
        referenceManager = currentProgram.getReferenceManager();

        int createdCount = createFunctionsAtDataReferencedCode();
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        decompiler.setSimplificationStyle("decompile");

        try (PrintWriter out = new PrintWriter(args[0], "UTF-8")) {
            out.println("# Pass 5 intro dump");
            out.println("# Functions created from data references: " + createdCount);
            out.println("# Plan: docs/superpowers/plans/2026-11-13-intro-decode.md");
            out.println();

            Set<Function> targets = collectTargetFunctions();
            writeTargetIndex(out, targets);
            writeGlobalReferences(out);
            writeRegisterArgumentCallSites(out);
            writeScriptPointerTable(out);
            writeDwordTable(out, "INTRO CYCLE TABLE", INTRO_CYCLE_TABLE, INTRO_CYCLE_TABLE_ENTRIES);
            writeAnimationTable(out);
            writeReferencedStrings(out, targets);
            for (Function function : targets) {
                if (monitor.isCancelled()) break;
                writeFunction(out, decompiler, function);
            }
        }
        println("Wrote " + args[0]);
    }

    // ---------------------------------------------------------------- targets

    private Set<Function> collectTargetFunctions() {
        Set<Function> targets = new TreeSet<>(Comparator.comparing(Function::getEntryPoint));
        for (Function function : functionManager.getFunctions(address(SCRIPT_FAMILY_START), true)) {
            if (function.getEntryPoint().getOffset() >= SCRIPT_FAMILY_END) break;
            if (!function.isThunk()) targets.add(function);
        }
        for (long helper : HELPER_FUNCTIONS) addFunctionContaining(targets, helper);
        // Whoever advances the step or consumes the step-done flag drives the script.
        addReferencingFunctions(targets, STEP_GLOBAL);
        addReferencingFunctions(targets, STEP_DONE_FLAG);
        // Whoever indexes the script pointer table decides when the intro starts.
        addReferencingFunctions(targets, SCRIPT_POINTER_TABLE);
        // Whoever creates the intro nodes (writes the node pointer globals).
        for (long node = 0x424384L; node <= 0x424394L; node += 4) addWritingFunctions(targets, node);
        return targets;
    }

    private void addFunctionContaining(Set<Function> targets, long offset) {
        Function function = functionManager.getFunctionContaining(address(offset));
        if (function == null) throw new IllegalStateException("no function at " + Long.toHexString(offset));
        targets.add(function);
    }

    private void addReferencingFunctions(Set<Function> targets, long offset) {
        for (Reference reference : referenceManager.getReferencesTo(address(offset))) {
            Function function = functionManager.getFunctionContaining(reference.getFromAddress());
            if (function != null) targets.add(function);
        }
    }

    private void addWritingFunctions(Set<Function> targets, long offset) {
        for (Reference reference : referenceManager.getReferencesTo(address(offset))) {
            if (!reference.getReferenceType().isWrite()) continue;
            Function function = functionManager.getFunctionContaining(reference.getFromAddress());
            if (function != null) targets.add(function);
        }
    }

    private void writeTargetIndex(PrintWriter out, Set<Function> targets) {
        out.println("## TARGET FUNCTIONS (" + targets.size() + ")");
        for (Function function : targets) {
            out.println(function.getEntryPoint() + "  " + function.getName()
                + "  size=" + function.getBody().getNumAddresses()
                + "  callers=" + String.join(", ", callerNames(function)));
        }
        out.println();
    }

    // ---------------------------------------------------------------- globals

    private void writeGlobalReferences(PrintWriter out) {
        out.println("## GLOBAL REFERENCES (" + hex(GLOBALS_START) + ".." + hex(GLOBALS_END) + " + extras)");
        for (long offset = GLOBALS_START; offset < GLOBALS_END; offset++) {
            writeReferencesTo(out, offset);
        }
        for (long offset : EXTRA_GLOBALS) writeReferencesTo(out, offset);
        out.println();
    }

    private void writeReferencesTo(PrintWriter out, long offset) {
        List<Reference> references = new ArrayList<>();
        for (Reference reference : referenceManager.getReferencesTo(address(offset))) references.add(reference);
        if (references.isEmpty()) return;
        references.sort(Comparator.comparing(Reference::getFromAddress));
        out.println("-- " + hex(offset) + "  (" + references.size() + " refs)");
        for (Reference reference : references) {
            Address from = reference.getFromAddress();
            Function function = functionManager.getFunctionContaining(from);
            Instruction instruction = listing.getInstructionAt(from);
            out.println("   " + from + "  " + accessKind(reference)
                + "  " + (function != null ? function.getName() : "?")
                + "  " + (instruction != null ? instruction.toString() : ""));
        }
    }

    private String accessKind(Reference reference) {
        RefType type = reference.getReferenceType();
        if (type.isRead() && type.isWrite()) return "RW   ";
        if (type.isWrite()) return "WRITE";
        if (type.isRead()) return "READ ";
        if (type.isCall()) return "CALL ";
        return "DATA ";
    }

    // ---------------------------------------------------------------- call sites

    private void writeRegisterArgumentCallSites(PrintWriter out) {
        out.println("## REGISTER-ARGUMENT CALL SITES (" + CALL_CONTEXT_INSTRUCTIONS + " instructions before each call)");
        for (long callee : REGISTER_ARGUMENT_CALLEES) {
            Function calleeFunction = functionManager.getFunctionAt(address(callee));
            String calleeName = calleeFunction != null ? calleeFunction.getName() : hex(callee);
            out.println("### calls to " + calleeName);
            List<Reference> calls = new ArrayList<>();
            for (Reference reference : referenceManager.getReferencesTo(address(callee))) {
                if (reference.getReferenceType().isCall()) calls.add(reference);
            }
            calls.sort(Comparator.comparing(Reference::getFromAddress));
            for (Reference call : calls) writeCallContext(out, call.getFromAddress());
        }
        out.println();
    }

    private void writeCallContext(PrintWriter out, Address callAddress) {
        Function caller = functionManager.getFunctionContaining(callAddress);
        out.println("-- " + callAddress + " in " + (caller != null ? caller.getName() : "?"));
        Deque<Instruction> context = new ArrayDeque<>();
        Instruction instruction = listing.getInstructionAt(callAddress);
        for (int index = 0; index <= CALL_CONTEXT_INSTRUCTIONS && instruction != null; index++) {
            context.addFirst(instruction);
            instruction = instruction.getPrevious();
        }
        for (Instruction line : context) out.println("   " + line.getAddress() + "  " + line);
    }

    // ---------------------------------------------------------------- data

    private void writeScriptPointerTable(PrintWriter out) throws MemoryAccessException {
        out.println("## SCRIPT POINTER TABLE @ " + hex(SCRIPT_POINTER_TABLE));
        for (int index = 0; index < SCRIPT_POINTER_TABLE_ENTRIES; index++) {
            long pointer = memory.getInt(address(SCRIPT_POINTER_TABLE + index * 4L)) & 0xffffffffL;
            Function function = functionManager.getFunctionAt(address(pointer));
            out.println("   [" + index + "] " + hex(pointer) + "  " + (function != null ? function.getName() : ""));
        }
        out.println();
    }

    private void writeDwordTable(PrintWriter out, String title, long start, int entries) throws MemoryAccessException {
        out.println("## " + title + " @ " + hex(start));
        for (int index = 0; index < entries; index++) {
            int value = memory.getInt(address(start + index * 4L));
            out.println("   [" + index + "] " + value + "  (" + hex(value & 0xffffffffL) + ")");
        }
        out.println();
    }

    private void writeAnimationTable(PrintWriter out) throws MemoryAccessException {
        out.println("## ANIMATION TABLE @ " + hex(ANIMATION_TABLE)
            + "  def=[id, frame_count, mode, frame_list]  frame=<5h raw>");
        for (int index = 0; index < ANIMATION_TABLE_MAX_ENTRIES; index++) {
            Address def = address(ANIMATION_TABLE + (long) index * ANIMATION_DEF_SIZE);
            int id = memory.getShort(def) & 0xffff;
            if (id != index) {
                out.println("   (table ends at index " + index + ": id field = " + id + ")");
                break;
            }
            int frameCount = memory.getShort(def.add(2)) & 0xffff;
            int mode = memory.getInt(def.add(4));
            long frameList = memory.getInt(def.add(8)) & 0xffffffffL;
            StringBuilder frames = new StringBuilder();
            for (int frame = 0; frame < frameCount; frame++) {
                Address entry = address(frameList + (long) frame * ANIMATION_FRAME_SIZE);
                frames.append(" (");
                for (int field = 0; field < 5; field++) {
                    if (field > 0) frames.append(',');
                    frames.append(memory.getShort(entry.add(field * 2L)));
                }
                frames.append(')');
            }
            out.println("   [" + index + " / " + hex(index) + "] count=" + frameCount + " mode=" + mode
                + " list=" + hex(frameList) + frames);
        }
        out.println();
    }

    private void writeReferencedStrings(PrintWriter out, Set<Function> targets) {
        out.println("## STRINGS REFERENCED FROM TARGET FUNCTIONS");
        for (Function function : targets) {
            for (Instruction instruction : listing.getInstructions(function.getBody(), true)) {
                for (Reference reference : instruction.getReferencesFrom()) {
                    Data data = listing.getDataAt(reference.getToAddress());
                    if (data == null || !StringDataInstance.isString(data)) continue;
                    out.println("   " + instruction.getAddress() + "  " + function.getName()
                        + "  " + data.getDefaultValueRepresentation());
                }
            }
        }
        out.println();
    }

    // ---------------------------------------------------------------- functions

    private void writeFunction(PrintWriter out, DecompInterface decompiler, Function function) {
        out.println("=================================================================");
        out.println("FUNCTION " + function.getName() + " @ " + function.getEntryPoint()
            + " size=" + function.getBody().getNumAddresses());
        out.println("CALLED BY: " + String.join(", ", callerNames(function)));
        out.println("----------------------------------------------------------------- decompiled");
        DecompileResults results = decompiler.decompileFunction(function, 120, monitor);
        if (results.decompileCompleted()) {
            out.println(results.getDecompiledFunction().getC());
        } else {
            out.println("// DECOMPILE FAILED: " + results.getErrorMessage());
        }
        out.println("----------------------------------------------------------------- disassembly");
        for (Instruction instruction : listing.getInstructions(function.getBody(), true)) {
            out.println(instruction.getAddress() + "  " + instruction);
        }
        out.println();
    }

    private Set<String> callerNames(Function function) {
        Set<String> callers = new TreeSet<>();
        for (Reference reference : referenceManager.getReferencesTo(function.getEntryPoint())) {
            Function caller = functionManager.getFunctionContaining(reference.getFromAddress());
            String kind = reference.getReferenceType().isFlow() ? "" : "(ptr)";
            callers.add((caller != null ? caller.getName() : reference.getFromAddress().toString()) + kind);
        }
        return callers;
    }

    // ---------------------------------------------------------------- shared

    /** Same as pass 4: pointer-only callbacks have no function until we create one. */
    private int createFunctionsAtDataReferencedCode() {
        int createdCount = 0;
        AddressIterator destinations = referenceManager.getReferenceDestinationIterator(
            memory.getExecuteSet(), true);
        while (destinations.hasNext()) {
            Address destination = destinations.next();
            if (functionManager.getFunctionContaining(destination) != null) continue;
            if (listing.getInstructionAt(destination) == null) continue;
            if (!hasDataReference(destination)) continue;
            if (new CreateFunctionCmd(destination).applyTo(currentProgram)) createdCount++;
        }
        return createdCount;
    }

    private boolean hasDataReference(Address destination) {
        for (Reference reference : referenceManager.getReferencesTo(destination)) {
            if (!reference.getReferenceType().isFlow()) return true;
        }
        return false;
    }

    private Address address(long offset) {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(offset);
    }

    private static String hex(long value) {
        return "0x" + Long.toHexString(value);
    }
}
