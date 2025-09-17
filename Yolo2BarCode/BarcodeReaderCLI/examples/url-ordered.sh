#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
INPDIR=./images

# ===== Read barcoded from Web-based images.   
# ===== Read multiple images with a single call, applying different 'type' option to each image 
$EXE $OPT $AUTH -type=pdf417 "https://wabr.inliteresearch.com/SampleImages/drvlic.ca.jpg" -type=code39  "https://www.dropbox.com/s/qcd8zfdvckwwdem/img39.pdf?dl=1" 


