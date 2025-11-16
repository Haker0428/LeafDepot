#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
INPDIR=./images

# ===== Read Code39 barcode.   Output is default JSON format
$EXE $OPT $AUTH -type=code39 "$INPDIR/test.tif"

# ===== Read Code39 barcode.  Output just text value to console
$EXE $OPT $AUTH -type=code39 "$INPDIR/test.tif" -format=text --output-text="{text}"

# Output new line
echo


