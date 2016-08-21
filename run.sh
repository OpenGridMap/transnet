#!/bin/bash
# launch a complete Transnet run

# configure the right matlab binary direction
matlab='/usr/local/MATLAB/R2016a/bin/matlab'

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "logs/$destdir"

# run transnet
cdir=`pwd`
cd app
python Transnet.py -p "../data/$destdir/pfile.poly" -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args | tee "../logs/$destdir/transnet.log"
cd $cdir

# run matlab
cdir=`pwd`
cd matlab
`$matlab -r "transform $destdir;quit;"` | tee "../logs/$destdir/transnet_matlab.log"
cd $cdir
