#!/bin/bash
# launch a complete Transnet run for planet


cdir=`pwd`
cd ../bash
./prepare_db_planet.sh
./prepare_planet_poly_and_voltages.sh
./run_planet_topology.sh
./run_planet_matlab.sh
cd $cdir