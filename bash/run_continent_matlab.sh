#!/bin/bash
# launch a complete Transnet run

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

machine=$(pwd)

if [[ $machine == *"epezhman"* ]]
then
    echo 'Machine: epezhman'
    matlab='/usr/local/bin/matlab'
elif [[ $machine == *"leimhofe"* ]]
then
    echo 'Machine: leimhofe'
    matlab='/usr/bin/matlab'
fi

mkdir -p "../logs/$destdir"


# run transnet
cdir=`pwd`
cd ../app

if [ "$#" -eq 2 ]; then
    mkdir -p "../logs/planet/$destdir"
    python Transnet.py -c $continent -m $matlab -g | tee "../logs/planet/$destdir/transnet.log"
else
    python Transnet.py -c $continent -m $matlab | tee "../logs/$destdir/transnet.log"
fi

cd $cdir

