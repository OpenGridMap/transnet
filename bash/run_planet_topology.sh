#!/bin/bash
# launch a complete Topology modeling for planet



#./run_continent.sh configs/continents/africa.conf
#./run_continent.sh configs/continents/asia.conf
#./run_continent.sh configs/continents/russia.conf
./run_continent.sh configs/continents/australiaoceania.conf
./run_continent.sh configs/continents/centralamerica.conf
#./run_continent.sh configs/continents/southamerica.conf
#./run_continent.sh configs/continents/europe.conf
#./run_continent.sh configs/continents/northamerica.conf
git add .
git commit -m "topology planet"
git push origin master