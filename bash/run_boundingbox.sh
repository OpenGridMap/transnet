#!/bin/bash
# launch a complete Transnet run


if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

mkdir -p "../logs/$destdir"

# matlab directory epezhman
matlab='/usr/local/bin/matlab'

# matlab directory remote
#matlab='/usr/bin/matlab'

# run transnet
cdir=`pwd`
cd app
python Transnet.py  -b "POLYGON((-125.3 49.2, -65.8 49.2, -65.8 24.0, -125.3 24.0, -125.3 49.2))" -D $dname -U $duser -X $dpassword -d $destdir -V $vlevels $trans_args | tee "../logs/$destdir/transnet.log"
cd $cdir

# run matlab
cdir=`pwd`
cd ../matlab
`$matlab -r "transform $destdir;quit;"` | tee "../logs/$destdir/transnet_matlab.log"
cd $cdir
