import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class pm_dataflow_3 extends GhidraScript {
    DecompInterface decomp;

    void decompileAt(long addrLong, String label) throws Exception {
        Address addr = toAddr(addrLong);
        Function f = getFunctionAt(addr);
        println("=== " + label + " @ " + addr + " ===");
        if (f == null) {
            f = getFunctionContaining(addr);
            println("  (not an exact entry point; containing fn = " + (f == null ? "NONE" : f.getName()+"@"+f.getEntryPoint()) + ")");
            if (f == null) return;
        }
        println("  --- callers ---");
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
        int n = 0;
        while (refs.hasNext() && n < 20) {
            Reference r = refs.next();
            println("    " + r.getFromAddress() + " type=" + r.getReferenceType());
            n++;
        }
        DecompileResults res = decomp.decompileFunction(f, 60, new ConsoleTaskMonitor());
        if (res.decompileCompleted()) {
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
        decompileAt(0x414dbcL, "notify/glow fn A (with duration/param)");
        decompileAt(0x414e38L, "notify/glow fn B (no param)");
        decomp.dispose();
    }
}
