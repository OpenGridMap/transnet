#!/bin/bash
# launch a complete Transnet run for planet

if [ "$#" -ne 0 ]; then
  # load the appropriate config file
  source "$1"
fi

cd $project_dir/bash
./prepare_db_planet.sh

cd $project_dir/bash
./prepare_planet_poly_and_voltages.sh

cd $project_dir/bash
./run_planet_topology.sh

cd $project_dir/bash
./run_planet_matlab.sh

cd $project_dir

git add .
git commit -m "modeling matlab planet"
git push origin master