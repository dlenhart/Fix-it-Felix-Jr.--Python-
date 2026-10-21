// Fourth pass: decompile EVERY function into one searchable file.
// Earlier passes targeted individual functions and missed the main loop and
// rendering code. Callbacks reached only through function-pointer tables
// have no function defined after auto-analysis (pass 3 had to force them),
// so this first creates functions at every data-referenced code address.
// Output path is the script's first argument.
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.*;

import java.io.PrintWriter;
import java.util.*;

public class GhidraPass4FullDump extends GhidraScript {

    @Override
    public void run() throws Exception {
        String outputPath = getScriptArgs()[0];
        Listing listing = currentProgram.getListing();
        FunctionManager functionManager = currentProgram.getFunctionManager();
        ReferenceManager referenceManager = currentProgram.getReferenceManager();

        int createdCount = createFunctionsAtDataReferencedCode(listing, functionManager, referenceManager);

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        decompiler.setSimplificationStyle("decompile");

        try (PrintWriter out = new PrintWriter(outputPath, "UTF-8")) {
            out.println("# Pass 4 full decompilation dump");
            out.println("# Functions created from data references: " + createdCount);
            out.println("# Total functions: " + functionManager.getFunctionCount());
            out.println();

            writeExternalCallers(out, functionManager, referenceManager);

            for (Function function : functionManager.getFunctions(true)) {
                if (monitor.isCancelled()) break;
                if (function.isExternal() || function.isThunk()) continue;
                writeFunction(out, decompiler, function, referenceManager);
            }
        }
        println("Wrote " + outputPath);
    }

    private int createFunctionsAtDataReferencedCode(Listing listing, FunctionManager functionManager,
                                                     ReferenceManager referenceManager) {
        int createdCount = 0;
        AddressIterator destinations = referenceManager.getReferenceDestinationIterator(
            currentProgram.getMemory().getExecuteSet(), true);
        while (destinations.hasNext()) {
            Address destination = destinations.next();
            if (functionManager.getFunctionContaining(destination) != null) continue;
            if (listing.getInstructionAt(destination) == null) continue;
            if (!hasDataReference(referenceManager, destination)) continue;
            if (new CreateFunctionCmd(destination).applyTo(currentProgram)) createdCount++;
        }
        return createdCount;
    }

    private boolean hasDataReference(ReferenceManager referenceManager, Address destination) {
        for (Reference reference : referenceManager.getReferencesTo(destination)) {
            if (!reference.getReferenceType().isFlow()) return true;
        }
        return false;
    }

    /** Lists every imported API with the functions that call it, e.g. glOrtho callers. */
    private void writeExternalCallers(PrintWriter out, FunctionManager functionManager,
                                      ReferenceManager referenceManager) {
        out.println("## IMPORTS AND CALLERS");
        for (Function external : functionManager.getExternalFunctions()) {
            Set<String> callers = new TreeSet<>();
            for (Address thunkOrSelf : thunkAddresses(external, functionManager)) {
                for (Reference reference : referenceManager.getReferencesTo(thunkOrSelf)) {
                    Function caller = functionManager.getFunctionContaining(reference.getFromAddress());
                    if (caller != null) callers.add(caller.getName());
                }
            }
            out.println(external.getParentNamespace().getName() + "::" + external.getName()
                + " <- " + String.join(", ", callers));
        }
        out.println();
    }

    private List<Address> thunkAddresses(Function external, FunctionManager functionManager) {
        List<Address> addresses = new ArrayList<>();
        addresses.add(external.getEntryPoint());
        for (Reference reference : currentProgram.getReferenceManager().getReferencesTo(external.getEntryPoint())) {
            addresses.add(reference.getFromAddress());
        }
        Address[] thunks = external.getFunctionThunkAddresses(true);
        if (thunks != null) addresses.addAll(Arrays.asList(thunks));
        return addresses;
    }

    private void writeFunction(PrintWriter out, DecompInterface decompiler, Function function,
                               ReferenceManager referenceManager) {
        Set<String> callers = new TreeSet<>();
        for (Reference reference : referenceManager.getReferencesTo(function.getEntryPoint())) {
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(reference.getFromAddress());
            String kind = reference.getReferenceType().isFlow() ? "" : "(ptr)";
            callers.add((caller != null ? caller.getName() : reference.getFromAddress().toString()) + kind);
        }
        out.println("=================================================================");
        out.println("FUNCTION " + function.getName() + " @ " + function.getEntryPoint()
            + " size=" + function.getBody().getNumAddresses());
        out.println("CALLED BY: " + String.join(", ", callers));
        out.println("-----------------------------------------------------------------");
        DecompileResults results = decompiler.decompileFunction(function, 120, monitor);
        if (results.decompileCompleted()) {
            out.println(results.getDecompiledFunction().getC());
        } else {
            out.println("// DECOMPILE FAILED: " + results.getErrorMessage());
        }
    }
}
