import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;

public class pm_dataflow_1 extends GhidraScript {
    void show(long litAddr, String label) throws Exception {
        Address a = toAddr(litAddr);
        Data d = getDataAt(a);
        println(label + " @ " + a + " -> " + (d == null ? "no data defined" : d.toString()));
        if (d != null && d.isPointer()) {
            Object v = d.getValue();
            println("   points to: " + v);
        } else {
            try {
                int val = getInt(a);
                println("   raw int32: 0x" + Integer.toHexString(val));
            } catch (Exception e) {}
        }
    }

    @Override
    public void run() throws Exception {
        show(0x422fa8L, "literal in fcn near 0x422f1c");
        show(0x423078L, "literal in fcn near 0x423018");
        show(0x423160L, "literal in fcn near 0x42308c");
        show(0x423218L, "literal in fcn near 0x4231b4");
    }
}
