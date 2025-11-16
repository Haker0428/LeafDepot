import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.File;

// javac brcli_example.java           ->  compile example
// java -cp . brcli_example           ->  use BarcodeReaderCLI command line 
// java -cp . brcli_example config    ->  use BarcodeReaderCLI configuration file  

public class brcli_example{
	
	public static String implode(String separator, String[] data) {
		StringBuilder sb = new StringBuilder();
		for (int i = 0; i < data.length - 1; i++) {
		//data.length - 1 => to not add separator at the end
			if (!data[i].matches(" *")) {//empty string are ""; " "; "  "; and so on
				sb.append(data[i]);
				sb.append(separator);
			}
		}
		sb.append(data[data.length - 1].trim());
		return sb.toString();
	}	
	
     public static void main(String []args)  throws IOException {
		boolean isWindows = System.getProperty("os.name").toLowerCase().startsWith("windows");
		File myDir = new File(brcli_example.class.getProtectionDomain().getCodeSource().getLocation().getPath());
		
		String exe;
		if (isWindows) exe  = "..\\bin\\BarcodeReaderCLI";
		else      	   exe = "../bin/BarcodeReaderCLI";
		
		String[] cargs = {
		exe,
		"-type=code128",
		"https://wabr.inliteresearch.com/SampleImages/1d.pdf"};

		String configFile = "./brcli-example.config";
		String[] cargsConfig = {
		exe,
		"@" + configFile};
		
		String cmd =  implode(" ", args.length > 0 ? cargsConfig : cargs);
        ProcessBuilder builder = new ProcessBuilder();

		if (isWindows) {
			builder.command("cmd.exe", "/c", cmd);
		} else {
			builder.command("sh", "-c", cmd);
		}
		builder.directory(myDir);
		builder.redirectErrorStream(true);
		Process process = builder.start();
		try (BufferedReader reader = new BufferedReader(
			new InputStreamReader(process.getInputStream()))) {
			String line;
			while ((line = reader.readLine()) != null) {
				System.out.println(line);
			}
		}
     }
}
