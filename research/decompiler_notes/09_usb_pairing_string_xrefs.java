import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Function;

public class usb_state_1 extends GhidraScript {

    void listAroundInsn(Address startSearch) throws Exception {
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
        while (insn != null && printed < 50) {
            println("  " + insn.getAddress() + ":  " + insn.toString());
            insn = insn.getNext();
            printed++;
        }
    }

    void investigate(long strAddr, String label) throws Exception {
        Address a = toAddr(strAddr);
        println("=== xrefs to string @ " + a + " (" + label + ") ===");
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(a);
        boolean any = false;
        while (refs.hasNext()) {
            any = true;
            Reference r = refs.next();
            Address from = r.getFromAddress();
            Function f = getFunctionContaining(from);
            println("  from " + from + " containing_fn=" + (f == null ? "NONE" : f.getName()+"@"+f.getEntryPoint()));
            listAroundInsn(from);
            println("");
        }
        if (!any) println("  (no xrefs found)");
        println("");
    }

    @Override
    public void run() throws Exception {
        investigate(0x434da1L, "enumerated");
        investigate(0x434dbdL, "power good");
        investigate(0x4179f0L, "pairing (2nd hit)");
    }
}
