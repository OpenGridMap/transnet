#!/bin/bash
# launch a complete Topology modeling for planet


./prepare_continent_poly_and_voltages.sh ../configs/continents/africa.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/asia.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/russia.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/australiaoceania.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/centralamerica.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/southamerica.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/europe.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/northamerica.conf -g
./prepare_continent_poly_and_voltages.sh ../configs/continents/usa.conf -g
