#  python brcli-example.py           ->  use BarcodeReaderCLI command line 
#  python brcli-example.py config    ->  use BarcodeReaderCLI configuration file  

import subprocess
import os
import sys

dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir)

exe = '../bin/BarcodeReaderCLI'

args = []
args.append(exe)
args.append('-type=code128')
args.append('https://wabr.inliteresearch.com/SampleImages/1d.pdf')

configFile = './brcli-example.config'
argsConfig = []
argsConfig.append(exe)
argsConfig.append('@' + configFile)

if len(sys.argv) > 1 : args = argsConfig
cp = subprocess.run(args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

output=cp.stdout
error=cp.stderr

if output != "": print("STDOUT:\n" + output)
if error != "":  print("STDERR:\n" + error)
# print("RETURN CODE:"  + str(print(cp.returncode)))