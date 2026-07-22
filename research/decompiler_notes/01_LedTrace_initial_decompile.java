import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class LedTrace extends GhidraScript {
    DecompInterface decomp;

    void decompileAndPrint(long addrLong, String label) throws Exception {
        Address addr = toAddr(addrLong);
        Function f = getFunctionAt(addr);
        println("=== " + label + " @ " + addr + " ===");
        if (f == null) {
            println("  NO FUNCTION DEFINED HERE");
            return;
        }
        println("  function: " + f.getName() + " body " + f.getBody());
        println("  --- callers (xrefs to entry) ---");
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(addr);
        while (refs.hasNext()) {
            Reference r = refs.next();
            println("    " + r.getFromAddress() + " -> " + addr + " type=" + r.getReferenceType());
        }
        DecompileResults res = decomp.decompileFunction(f, 60, new ConsoleTaskMonitor());
        if (res.decompileCompleted()) {
            println("  --- decompiled ---");
            println(res.getDecompiledFunction().getC());
        } else {
            println("  DECOMPILE FAILED: " + res.getErrorMessage());
        }
        println("");
    }

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        decompileAndPrint(0x41d7a8L, "wrapper (color request entry)");
        decompileAndPrint(0x41dbf0L, "low-level PWM writer");
        decompileAndPrint(0x41e7d8L, "off-path function");
        decompileAndPrint(0x419250L, "channel scale function");

        decomp.dispose();
    }
}
