#!/bin/bash
# launch a complete Transnet run for planet

machine=$(pwd)

if [[ $machine == *"epezhman"* ]]
then
    echo 'Machine: epezhman'
    cd /home/epezhman/Projects/transnet/bash
elif [[ $machine == *"leimhofe"* ]]
then
    echo 'Machine: leimhofe'
    cd /home/leimhofe/transnet/bash
fi

source activate transnet

which python > ../logs/python_ver.txt

export HTTP_PROXY="http://proxy:8080"
export HTTPS_PROXY="https://proxy:8080"

mkdir -p "../../transnet-models/logs"

cat /dev/null > ../../transnet-models/logs/planet_db.log
cat /dev/null > ../../transnet-models/logs/planet_poly_and_voltages.log
cat /dev/null > ../../transnet-models/logs/planet_topology.log
cat /dev/null > ../../transnet-models/logs/planet_matlab.log
cat /dev/null > ../../transnet-models/logs/whole_continent_topology.log
cat /dev/null > ../../transnet-models/logs/whole_continent_matlab.log


./_prepare_db_planet.sh | tee -a "../../transnet-models/logs/planet_db.log"

./_prepare_planet_poly_and_voltages.sh | tee -a "../../transnet-models/logs/planet_poly_and_voltages.log"

./_run_planet_topology.sh | tee -a "../../transnet-models/logs/planet_topology.log"

#./_run_planet_matlab.sh | tee -a "../../transnet-models/logs/planet_matlab.log"

./_run_whole_continent_topology.sh | tee -a "../../transnet-models/logs/whole_continent_topology.log"

#./_run_whole_continent_matlab.sh | tee -a "../../transnet-models/logs/whole_continent_matlab.log"

cd ../../transnet-models
git add .
git commit -m "modeling continents"
git push origin master
