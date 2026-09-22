// Export selected functions as pseudocode from a LOCAL COPY of a vendor ELF.
// Run with analyzeHeadless, -postScript DecompileBoxSelection.java OUT FILTER...
// Does not execute the input program or modify robot binaries.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class DecompileBoxSelection extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) throw new IllegalArgumentException("OUT FILTER [FILTER...]");
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(Files.newBufferedWriter(
                Path.of(args[0]), StandardCharsets.UTF_8))) {
            out.println("// GHIDRA PSEUDOCODE: reconstructed, not original source or validated replacement.");
            out.println("// Program: " + currentProgram.getName());
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                String name = function.getName(true);
                boolean selected = false;
                for (int i = 1; i < args.length; i++) {
                    if (name.contains(args[i])) selected = true;
                }
                if (!selected || function.isThunk() || function.isExternal()) continue;
                out.println("\n// FUNCTION " + function.getEntryPoint() + " " + name);
                DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
                if (result.decompileCompleted()) out.println(result.getDecompiledFunction().getC());
                else out.println("// DECOMPILE_FAILED: " + result.getErrorMessage());
                out.flush();
                println("EXPORTED " + function.getEntryPoint() + " " + name);
            }
        } finally {
            decompiler.dispose();
        }
    }
}
