# encoding: utf-8
#  ruby brcli-example.rb           ->  use BarcodeReaderCLI command line 
#  ruby brcli-example.rb config    ->  use BarcodeReaderCLI configuration file  

require 'open3'
dir = File.dirname(__FILE__)  # enable 'require' use modules in script folder
Dir.chdir(dir)

args  = Array[
'../bin/BarcodeReaderCLI',
'-type=code128',
'"https://wabr.inliteresearch.com/SampleImages/1d.pdf"',
]

configFile = './brcli-example.config'
argsConfig  = Array[
'../bin/BarcodeReaderCLI',
'@"' + configFile + '"'
]

args = argsConfig  if ARGV.length > 0
params = args.join(' ')
output, error, status = Open3.capture3(params)

if output != "" then  
  puts "STDOUT:\n " + output
end
if error != "" then 
   puts "STDERR:\n " + error
end

