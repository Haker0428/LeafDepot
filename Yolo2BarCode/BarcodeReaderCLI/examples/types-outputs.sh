#!/bin/bash

HERE="$(dirname "$(readlink -f "${0}")")"
cd $HERE

EXE=../bin/BarcodeReaderCLI
OUTDIR=/tmp/brcli
INPDIR=./images
rm -rf $OUTDIR
mkdir -p $OUTDIR

# ===== Read availbale barcode types
# ===== Save output in JSON and CSV formats
$EXE $OPT  $AUTH -type=pdf417,qr,datamatrix,code39,code128,codabar,ucc128,code93,upca,ean8,upce,ean13,i25,imb,bpo,aust,sing   "$INPDIR/types.pdf" -output="$OUTDIR/types.json" -output="$OUTDIR/types.csv" 

echo Output is written to $OUTDIR folder
ls $OUTDIR

