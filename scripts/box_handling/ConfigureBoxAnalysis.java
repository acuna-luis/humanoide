// Avoid heuristic no-return propagation through imported C++ logging functions.
import ghidra.app.script.GhidraScript;
import java.util.Map;

public class ConfigureBoxAnalysis extends GhidraScript {
    @Override
    public void run() throws Exception {
        Map<String, String> options = getCurrentAnalysisOptionsAndValues(currentProgram);
        for (String name : options.keySet()) {
            if (name.contains("Non-Returning") || name.contains("Exception")) {
                println("ANALYSIS_OPTION " + name + "=" + options.get(name));
            }
            if (name.equals("Non-Returning Functions - Discovered") ||
                name.equals("GCC Exception Handlers")) {
                setAnalysisOption(currentProgram, name, "false");
            }
        }
    }
}
