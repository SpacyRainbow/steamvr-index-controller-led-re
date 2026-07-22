import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

public class LedTrace9 extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address addr = toAddr(0x41d859L);
        Address endAddr = toAddr(0x41dac4L);
        Instruction insn = getInstructionAt(addr);
        if (insn == null) {
            // force disassembly if not already covered
            disassemble(addr);
            insn = getInstructionAt(addr);
        }
        while (insn != null && insn.getAddress().getOffset() < endAddr.getOffset()) {
            println(insn.getAddress() + ":  " + insn.toString());
            insn = insn.getNext();
        }
    }
}
