// Scan float globals referenced in decompiled callback functions
// @category Analysis
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;

public class GhidraFloats extends GhidraScript {
    @Override
    public void run() throws Exception {
        AddressFactory af = currentProgram.getAddressFactory();

        // Addresses referenced by the decompiled Felix state callback functions
        String[] addrs = {
            // From state 0 (idle/input): movement direction speeds
            "00416b08", "00416b10", "00416b18",
            "00416b40", "00416b44",
            "00416b80", "00416b88", "00416b8c",
            // From state 5 (hammer): timing values
            "00416b60", "00416b68", "00416b70", "00416b78",
            // From states 6/9 (falling/dying): gravity
            "00416be8", "00416b58",
        };

        println("=== REFERENCED FLOAT GLOBALS ===");
        for (String addrStr : addrs) {
            try {
                Address addr = af.getAddress("0x" + addrStr);
                byte[] bytes = new byte[4];
                currentProgram.getMemory().getBytes(addr, bytes);
                int intVal = (bytes[0] & 0xFF) | ((bytes[1] & 0xFF) << 8) |
                             ((bytes[2] & 0xFF) << 16) | ((bytes[3] & 0xFF) << 24);
                float floatVal = Float.intBitsToFloat(intVal);
                println("_DAT_" + addrStr + " = int:" + intVal +
                        " (0x" + Integer.toHexString(intVal) + ") float:" + floatVal);
            } catch (Exception e) {
                println("_DAT_" + addrStr + " = [error: " + e.getMessage() + "]");
            }
        }

        // Full scan of 0x416b00-0x416bff for completeness
        println("\n=== FULL SCAN 0x416b00-0x416bff ===");
        for (int i = 0; i < 64; i++) {
            String addrStr = String.format("00416b%02x", i * 4);
            try {
                Address addr = af.getAddress("0x" + addrStr);
                byte[] bytes = new byte[4];
                currentProgram.getMemory().getBytes(addr, bytes);
                int intVal = (bytes[0] & 0xFF) | ((bytes[1] & 0xFF) << 8) |
                             ((bytes[2] & 0xFF) << 16) | ((bytes[3] & 0xFF) << 24);
                float floatVal = Float.intBitsToFloat(intVal);
                if (intVal != 0) {
                    println("DAT_" + addrStr + " = int:" + intVal +
                            " (0x" + Integer.toHexString(intVal) + ") float:" + floatVal);
                }
            } catch (Exception e) {}
        }

        // Also scan player bounds at 0x42425c and 0x424260 (referenced as Y bounds)
        println("\n=== PLAYER Y BOUNDS ===");
        String[] boundAddrs = {"0042425c", "00424260"};
        for (String addrStr : boundAddrs) {
            try {
                Address addr = af.getAddress("0x" + addrStr);
                byte[] bytes = new byte[4];
                currentProgram.getMemory().getBytes(addr, bytes);
                int intVal = (bytes[0] & 0xFF) | ((bytes[1] & 0xFF) << 8) |
                             ((bytes[2] & 0xFF) << 16) | ((bytes[3] & 0xFF) << 24);
                float floatVal = Float.intBitsToFloat(intVal);
                println("_DAT_" + addrStr + " = int:" + intVal +
                        " (0x" + Integer.toHexString(intVal) + ") float:" + floatVal);
            } catch (Exception e) {
                println("_DAT_" + addrStr + " = [error: " + e.getMessage() + "]");
            }
        }

        println("\nFLOAT SCAN COMPLETE.");
    }
}
