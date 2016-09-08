#!/bin/bash
# launch a complete Transnet run for planet

cd /home/leimhofe/transnet/bash

source activate transnet

#./prepare_db_planet.sh | tee -a "../logs/planet_db.log"

#./prepare_planet_poly_and_voltages.sh | tee -a "../logs/planet_poly_and_voltages.log"

#./run_planet_topology.sh | tee -a "../logs/planet_topology.log"

#./run_planet_matlab.sh | tee -a "../logs/planet_matlab.log"

cd ..

which python > sd.txt

git checkout planet-models
git add .
git commit -m "modeling planet"
git push origin planet-models
