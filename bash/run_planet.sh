#!/bin/bash
# launch a complete Transnet run for planet

cd /home/leimhofe/transnet/bash

source activate transnet

which python > ../logs/python_ver.txt

export HTTP_PROXY="http://proxy:8080"
export HTTPS_PROXY="https://proxy:8080"

#./prepare_db_planet.sh | tee -a "../logs/planet_db.log"

./prepare_planet_poly_and_voltages.sh | tee -a "../logs/planet_poly_and_voltages.log"

#./run_planet_topology.sh | tee -a "../logs/planet_topology.log"

#./run_planet_matlab.sh | tee -a "../logs/planet_matlab.log"

cd ..

git checkout planet-models
git add .
git commit -m "modeling planet"
git push origin planet-models
