#!/bin/sh
# launch a complete Transnet run

# configure the right matlab binary direction
matlab='/Applications/MATLAB_R2016a.app/bin/matlab'

# load the appropriate config file
source "$1"

# run transnet
cdir=`pwd`
cd code
python Transnet.py -p "../data/$destdir/pfile.poly" -D $dname -U $duser -X $dpassword -t -l -d $destdir -V $vlevels
cd $cdir

# run matlab
cdir=`pwd`
cd matlab
`$matlab -r "transform $destdir;quit;"` 
cd $cdir
