#!/bin/bash
# launch a complete Transnet run for planet

cd /home/leimhofe/transnet

source activate transnet

./prepare_db_planet.sh

./prepare_planet_poly_and_voltages.sh

./run_planet_topology.sh

./run_planet_matlab.sh

cd ..

git checkout planet-models
git add .
git commit -m "modeling matlab planet"
git push origin planet-models