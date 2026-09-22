// Read-only inspection of the locally imported Cruzr S2 v0.2.0 ELF.
// Addresses below refer to the Ghidra import with image base 0x100000.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.InstructionIterator;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class InspectArcPrecise extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("OUTPUT");
        try (PrintWriter out = new PrintWriter(Files.newBufferedWriter(
                Path.of(args[0]), StandardCharsets.UTF_8))) {
            out.println("Program: " + currentProgram.getName());
            out.println("Image base: " + currentProgram.getImageBase());
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext()) {
                Function f = functions.next();
                String name = f.getName(true);
                if (!name.contains("ArcPreciseController::") || f.isThunk() || f.isExternal()) continue;
                if (!(name.endsWith("setStartToGoal") || name.endsWith("preciseControl")
                        || name.endsWith("setNaviSpeed") || name.endsWith("setNaviGoalLevel"))) continue;
                out.println("\nFUNCTION " + name + " " + f.getEntryPoint());
                InstructionIterator instructions = currentProgram.getListing().getInstructions(f.getBody(), true);
                while (instructions.hasNext()) {
                    var instruction = instructions.next();
                    out.println(instruction.getAddress() + " " + instruction);
                }
            }
            out.println("\nRODATA doubles (version-specific addresses)");
            for (long a = 0x141378; a <= 0x1413e0; a += 8) {
                out.printf("%x %.17g%n", a, Double.longBitsToDouble(
                        currentProgram.getMemory().getLong(toAddr(a))));
            }
            out.println("\nShort setters, including functions classified as thunks");
            for (long a : new long[] {0x126ce4, 0x1290b0, 0x1290c0, 0x1290e0}) {
                var instruction = currentProgram.getListing().getInstructionAt(toAddr(a));
                for (int i = 0; instruction != null && i < 8; i++) {
                    out.println(instruction.getAddress() + " " + instruction);
                    if (instruction.getMnemonicString().equals("ret")) break;
                    instruction = instruction.getNext();
                }
            }
        }
    }
}
