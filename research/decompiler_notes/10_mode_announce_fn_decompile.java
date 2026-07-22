import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.util.task.ConsoleTaskMonitor;
import ghidra.program.model.listing.Data;

public class usb_state_4 extends GhidraScript {
    DecompInterface decomp;

    void decompileAt(long addrLong, String label) throws Exception {
        Address addr = toAddr(addrLong);
        Function f = getFunctionAt(addr);
        println("=== " + label + " @ " + addr + " ===");
        if (f == null) {
            f = getFunctionContaining(addr);
            if (f == null) { println("  no function"); return; }
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

    void showLiteral(long litAddr, String label) throws Exception {
        Address a = toAddr(litAddr);
        Data d = getDataAt(a);
        println(label + " @ " + a + " -> " + (d == null ? "no data defined" : d.toString()));
        try {
            int val = getInt(a);
            println("   raw int32: 0x" + Integer.toHexString(val));
        } catch (Exception e) {}
    }

    @Override
    public void run() throws Exception {
        decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        decompileAt(0x417914L, "pairing-related init function");
        showLiteral(0x417a08L, "struct base literal used at end of that function");
        decomp.dispose();
    }
}
