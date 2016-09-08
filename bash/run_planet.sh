#!/bin/bash
# launch a complete Transnet run for planet

#cd /home/leimhofe/transnet/bash

cd /home/epezhman/Projects/transnet/bash

source activate transnet

which python > ../logs/python_ver.txt

#export HTTP_PROXY="http://proxy:8080"
#export HTTPS_PROXY="https://proxy:8080"

#./prepare_db_planet.sh | tee -a "../logs/planet_db.log"

#./prepare_planet_poly_and_voltages.sh | tee -a "../logs/planet_poly_and_voltages.log"

#./run_planet_topology.sh | tee -a "../logs/planet_topology.log"

#./run_planet_matlab.sh | tee -a "../logs/planet_matlab.log"

cd ..

git checkout planet-models
git add .
git commit -m "modeling countries of continent"
git push origin planet-models

cd bash

./prepare_whole_continent_poly_and_voltages.sh | tee -a "../logs/planet_poly_and_voltages.log"

./run_whole_continent_topology.sh | tee -a "../logs/whole_continent_topology.log"

./run_whole_continent_matlab.sh | tee -a "../logs/whole_continent_matlab.log"

git checkout planet-models
git add .
git commit -m "modeling continents"
git push origin planet-models
