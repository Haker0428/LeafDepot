package main

import (
 "os/exec"
 . "fmt"
 "runtime"
 "bytes"
 "os"
)

// go run brcli-example.go           ->  use BarcodeReaderCLI command line 
// go run brcli-example.go config    ->  use BarcodeReaderCLI configuration file  

func main() {
	isWindows := runtime.GOOS == "windows"
	exe, shell, flag := "../bin/BarcodeReaderCLI", "sh", "-c"
	if isWindows {
		exe, shell, flag = "..\\bin\\BarcodeReaderCLI", "cmd.exe", "/c"
	} 

	args := []string{
		exe,
		"-type=code128",
		"https://wabr.inliteresearch.com/SampleImages/1d.pdf"}

	configFile := "./brcli-example.config"
	argsCongig := []string{
		exe,
		"@" + configFile + ""}
	
	cmd := ""
	if (len(os.Args) > 1){
		for _, s := range argsCongig {cmd = cmd + s + " "}
	} else {
		for _, s := range args {cmd = cmd + s + " "}
	}
	 
    proc := exec.Command(shell, flag, cmd)
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	proc.Stdout = &stdout
	proc.Stderr = &stderr
	proc.Run()
	
	if stdout.Len() > 0 { Print("STDOUT: \n" + stdout.String())}
    if stderr.Len() > 0  { Print("STDERR: \n" + stderr.String())}
}