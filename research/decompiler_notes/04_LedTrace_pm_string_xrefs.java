import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.task.ConsoleTaskMonitor;

public class LedTrace13 extends GhidraScript {
    DecompInterface decomp;

    void handle(long strAddr, String label) throws Exception {
        Address addr = toAddr(strAddr);
        println("=== xrefs to string " + label + " @ " + addr + " ===");
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(addr);
        while (refs.hasNext()) {
            Reference r = refs.next();
            Address from = r.getFromAddress();
            Function f = getFunctionContaining(from);
            println("  " + from + " in function " + (f == null ? "NONE" : f.getName() + "@" + f.getEntryPoint()));
            if (f != null) {
                DecompileResults res = decomp.decompileFunction(f, 60, new ConsoleTaskMonitor());
                if (res.decompileCompleted()) {
                    println(res.getDecompiledFunction().getC());
                } else {
                    println("  decompile failed: " + res.getErrorMessage());
                }
            }
        }
        println("");
    }

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        handle(0x422fabL, "PM -> charging");
        handle(0x4231a0L, "PM: charging -> on");
        decomp.dispose();
    }
}
