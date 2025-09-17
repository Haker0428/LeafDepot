// csi brcli-example.csx           ->  use BarcodeReaderCLI command line
// csi brcli-example.csx config    ->  use BarcodeReaderCLI configuration file e
//    csi is installed on Windows with Visual Studio in C:\Program Files (x86)\MSBuild\{version}\Bin
//    csi is installed on Linux with Mono

using System;
using System.IO;
using System.Runtime.CompilerServices;

static string thisDirectory([CallerFilePath] string path = "") => Path.GetDirectoryName(path);
Directory.SetCurrentDirectory(thisDirectory());

string exe = "../bin/BarcodeReaderCLI";
string[] args = {
"-type=code128",
"https://wabr.inliteresearch.com/SampleImages/1d.pdf",
};

// Obtain options and sources from a configuration file
string configFile = "./brcli-example.config";
string[] argsConfig = {"@\"" + configFile + "\""};

string output;
string error;

using (Process proc = new Process())
{
    proc.StartInfo = new ProcessStartInfo   {
        FileName = exe,
        Arguments = string.Join(" ",  (Args.Count > 0) ? argsConfig : args),
        UseShellExecute = false,
        RedirectStandardOutput = true,
        RedirectStandardError = true,
    };
	proc.Start();
	error = proc.StandardError.ReadToEnd();
	output = proc.StandardOutput.ReadToEnd();
	proc.WaitForExit();
};

if (output != "") Console.WriteLine("STDOUT:\n" + output);
if (error != "") Console.WriteLine("STDERR:\n" + error);
