import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class LedTrace3 extends GhidraScript {
    DecompInterface decomp;

    void decompileContaining(long addrLong, String label) throws Exception {
        Address addr = toAddr(addrLong);
        Function f = getFunctionContaining(addr);
        println("=== " + label + " (addr " + addr + ") ===");
        if (f == null) {
            println("  NO FUNCTION CONTAINS THIS ADDRESS");
            return;
        }
        println("  containing function: " + f.getName() + " entry=" + f.getEntryPoint() + " body=" + f.getBody());
        println("  --- callers of this function's entry ---");
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
        while (refs.hasNext()) {
            Reference r = refs.next();
            println("    " + r.getFromAddress() + " -> " + f.getEntryPoint() + " type=" + r.getReferenceType());
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

        decompileContaining(0x41d718L, "caller 1 of wrapper");
        decompileContaining(0x41d958L, "caller 2 of wrapper");
        decompileContaining(0x41daa4L, "caller 3 of wrapper");
        decompileContaining(0x41d7acL, "the wrapper itself (real entry)");

        decomp.dispose();
    }
}
