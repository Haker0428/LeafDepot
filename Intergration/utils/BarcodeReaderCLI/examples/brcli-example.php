<?php
// php brcli-example.php          ->  use BarcodeReaderCLI command line 
// php brcli-example.php config   ->  use BarcodeReaderCLI configuration file 
chdir(__DIR__);

$args = array(
'"../bin/BarcodeReaderCLI"',
'-type=code128',
'"https://wabr.inliteresearch.com/SampleImages/1d.pdf"',
);

$configFile = './brcli-example.config';
$argsConfig = array(
'"../bin/BarcodeReaderCLI"',
'@"' . $configFile . '"',
);

function doExec($cmd, &$stdout=null, &$stderr=null) {
    $proc = proc_open($cmd,[
        1 => ['pipe','w'],
        2 => ['pipe','w'],
    ],$pipes);
    $stdout = stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    $stderr = stream_get_contents($pipes[2]);
    fclose($pipes[2]);
    return proc_close($proc);
}

$output = ""; $error = "";
$params = implode(" ", $argc > 1 ?  $argsConfig : $args);
if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') $params = '"' . $params . '"'; 

doExec($params, $output, $error);
if ($output != "") echo "STDOUT:\n $output";
if ($error != "") echo "STDERR:\n $error";
?>