import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;

public class LedTrace15 extends GhidraScript {
    @Override
    public void run() throws Exception {
        FunctionManager fm = currentProgram.getFunctionManager();
        println("=== functions in range 0x422800-0x423300 (wider context) ===");
        for (Function fn : fm.getFunctions(toAddr(0x422800L), true)) {
            if (fn.getEntryPoint().getOffset() > 0x423300L) break;
            println("  " + fn.getEntryPoint() + "  " + fn.getName() + "  body=" + fn.getBody());
        }
        println("");
        println("=== linear listing 0x422e60 - 0x423250 ===");
        long a = 0x422e60L;
        long end = 0x423250L;
        while (a < end) {
            Address addr = toAddr(a);
            Instruction insn = getInstructionAt(addr);
            if (insn == null) {
                try { disassemble(addr); } catch (Exception e) {}
                insn = getInstructionAt(addr);
            }
            if (insn == null) {
                a += 1;
                continue;
            }
            println(insn.getAddress() + ":  " + insn.toString());
            a = insn.getAddress().getOffset() + insn.getLength();
        }
    }
}
