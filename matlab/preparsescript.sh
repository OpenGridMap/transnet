#!/bin/sh
# makes the cim model MATLAB "readable"
cat $1 | sed 's/cim://g' | sed 's/rdf:ID/ID/g' | sed -E 's/rdf:resource=\"([#]?)/rdf_resource=\"/g' | sed -E 's/<([A-Za-z]*)\.([A-Za-z]*)>(.*)<\/([A-Za-z]*)\.([A-Za-z]*)>/<\1_\2>\3<\/\4_\5>/g' | sed -E 's/<([A-Za-z]*)\.([A-Za-z]*) /<\1_\2\ /g' > $2
