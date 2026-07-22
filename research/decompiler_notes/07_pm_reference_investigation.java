import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class pm_dataflow_2 extends GhidraScript {

    void listAroundInsn(Address startSearch, String label) throws Exception {
        Instruction cur = getInstructionAt(startSearch);
        Instruction start = cur;
        int steps = 0;
        while (start != null && steps < 60) {
            Instruction prev = start.getPrevious();
            if (prev == null) break;
            String m = prev.getMnemonicString();
            if (m != null && m.startsWith("push") && prev.toString().contains("lr")) {
                start = prev;
                break;
            }
            start = prev;
            steps++;
        }
        Instruction insn = start;
        int printed = 0;
        while (insn != null && printed < 40) {
            println("  " + insn.getAddress() + ":  " + insn.toString());
            insn = insn.getNext();
            printed++;
        }
    }

    void investigate(long litAddr) throws Exception {
        Address litA = toAddr(litAddr);
        println("=== literal word at " + litA + " ===");
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(litA);
        boolean any = false;
        while (refs.hasNext()) {
            any = true;
            Reference r = refs.next();
            Address from = r.getFromAddress();
            Function f = getFunctionContaining(from);
            println("  referenced from " + from + " type=" + r.getReferenceType() +
                    " containing_fn=" + (f == null ? "NONE(unbounded)" : f.getName() + "@" + f.getEntryPoint()));
            println("  --- context around " + from + " ---");
            listAroundInsn(from, "");
            println("");
        }
        if (!any) {
            println("  (no references found via reference manager)");
        }
        println("");
    }

    @Override
    public void run() throws Exception {
        long[] addrs = {
            0x417f00L, 0x4193d0L, 0x419c68L, 0x419d3cL, 0x419d6cL, 0x419de4L,
            0x41c334L, 0x41d0b8L, 0x41e37cL, 0x41ebd8L, 0x420938L, 0x420994L,
            0x4258fcL, 0x42984cL
        };
        for (long a : addrs) {
            investigate(a);
        }
    }
}
