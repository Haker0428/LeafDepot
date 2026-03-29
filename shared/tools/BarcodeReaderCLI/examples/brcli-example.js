// node brcli-example.js           ->  use BarcodeReaderCLI command line 
// node brcli-example.js config    ->  use BarcodeReaderCLI configuration file  

var cp = require('child_process');
process.chdir(__dirname);

var exe = '../bin/BarcodeReaderCLI';
var args = [];
args.push('-type=code128');
args.push('https://wabr.inliteresearch.com/SampleImages/1d.pdf');

var configFile = "./brcli-example.config";
var argsConfig = []; 
argsConfig.push('@' + configFile);
 
const proc = cp.spawn(exe, process.argv.length > 2 ? argsConfig : args);
proc.stdout.on('data', (data) => {
    console.log(data.toString());
});
proc.stderr.on('data', (data) => {
    console.error(data.toString());
});
