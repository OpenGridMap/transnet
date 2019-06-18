function preparsescript(srcFullFileName, dstFullFileName)

fin = fopen(srcFullFileName,'r');
[~,~,machinefmt,encoding] = fopen(fin);
cont = fread(fin,Inf,'*char')';
fclose(fin);

cont = regexprep(cont,'cim:','');
cont = regexprep(cont,'rdf:ID','ID');
cont = regexprep(cont,'rdf:resource=\"([#]?)','rdf_resource=\"');
cont = regexprep(cont,'<([A-Za-z]*)\.([A-Za-z]*)>(.*)</([A-Za-z]*)\.([A-Za-z]*)>','<$1_$2>$3<\/$4_$5>','dotexceptnewline');
cont = regexprep(cont,'<([A-Za-z]*)\.([A-Za-z]*) ', '<$1_$2\ ','dotexceptnewline');

fout = fopen(dstFullFileName,'w',machinefmt,encoding);
fwrite(fout,cont,'char');
fclose(fout);


