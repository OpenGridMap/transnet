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

cat /dev/null > ../configs/evals/_evals.log

./run_country.sh ../configs/evals/austria.conf | tee -a "../configs/evals/_evals.log"

./run_country.sh ../configs/evals/germany.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/bayern.conf | tee -a "../configs/evals/_evals.log"

./run_country.sh ../configs/evals/algeria.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/belgium.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/brazil.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/chile.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/denmark.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/egypt.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/france.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/gb.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/india.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/ireland.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/italy.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/japan.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/morocco.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/netherlands.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/poland.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/southafrica.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/spain.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/turkey.conf | tee -a "../configs/evals/_evals.log"
./run_country.sh ../configs/evals/usa.conf | tee -a "../configs/evals/_evals.log"
