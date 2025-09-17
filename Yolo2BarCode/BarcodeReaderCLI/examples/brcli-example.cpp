// Your First C++ Program

// g++ -o _example  brcli-example.cpp           ->  compile example
// _example           ->  use BarcodeReaderCLI command line 
// _example config          ->  use BarcodeReaderCLI configuration file  
// On Linux use ./_example

#include <iostream>
#include <string>
#include <memory>

std::string exec(const char* cmd) {
    std::array<char, 128> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);
    if (!pipe) {
        return "popen() failed!";
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

int main(int argc, char *argv[]) {
#if defined _WIN32 || defined _WIN64
	std::string exe  = "..\\bin\\BarcodeReaderCLI";
#else		
	std::string exe = "../bin/BarcodeReaderCLI";
#endif	

	std::string cmd = "";
	if (argc > 1)	{
		std::string configFile = "./brcli-example.config";
		std::string cargsConfig[] = {
			exe,
			"@" + configFile};	
		for (int i = 0; i < sizeof(cargsConfig)/sizeof(cargsConfig[0]); i++)
			cmd += cargsConfig[i] + " ";
	}
	else {
		std::string cargs[] = {
			exe,
			"-type=code128",
			"https://wabr.inliteresearch.com/SampleImages/1d.pdf"};
		for (int i = 0; i < sizeof(cargs)/sizeof(cargs[0]); i++)
			cmd += cargs[i] + " ";
	}
	
	std::string out = exec(cmd.c_str());
    std::cout << out << std::endl;
    return 0;
}
