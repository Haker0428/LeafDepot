#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
INPDIR=./images

# ===== Read barcode in a folder and sub-folders.  Linit file types to BMP and PDF
$EXE $OPT $AUTH -type=pdf417 -sub -incl="*.bmp *.pdf" "$INPDIR/"


