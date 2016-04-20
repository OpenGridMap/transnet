function transformCimToSimulink()

    % simplify cim model to be better readable by MATLAB
    system('sh preparsescript.sh /home/lej/PycharmProjects/transnet/results/cim_pretty.xml matcim.xml')

    % reed cim objects
    [tree treeName] = xml_read ('matcim.xml');
    transformers = tree(1).PowerTransformer;
    transformerWindings = tree(1).TransformerWinding;
    connectivityNodes = tree(1).ConnectivityNode;
    terminals = tree(1).Terminal;
    lines = tree(1).ACLineSegment;
    generators = tree(1).SynchronousMachine;
    loads = tree(1).EnergyConsumer;
    load_characteristics = tree(1).LoadResponseCharacteristic;

    mdl = 'model';
    close_system('model');
    open(mdl);
    %mdl = open('test_model')

    for i = 1:length(transformers)
       block = add_block('block_templates/transformer',[mdl,'/',transformers(i).IdentifiedObject_name]);
       transformers(i).block = block;
       transformers(i).type = 'transformer';
    end
    
    for i = 1:length(transformerWindings)
       transformerWindings(i).type = 'transformerWinding';
       transformer = getWindingTransformer(transformerWindings(i), transformers);
       transformerWindings(i).block = transformer.block;
    end
    
    for i = 1:length(generators)
       block = add_block('block_templates/generator',[mdl,'/',generators(i).IdentifiedObject_name]);
       generators(i).block = block;
       generators(i).type = 'generator';
    end
    
    for i = 1:length(loads)
       block = add_block('block_templates/load',[mdl,'/',loads(i).IdentifiedObject_name]);
       loads(i).block = block;
       loads(i).type = 'load';
    end
    
    for i = 1:length(lines)
       block = add_block('block_templates/line',[mdl,'/line',lines(i).IdentifiedObject_name]);
       lines(i).block = block;
       lines(i).type = 'line';
    end
    
    for i = 1:length(connectivityNodes)
       equipments = {};
       matchingTerminals = getTerminals(connectivityNodes(i), terminals);
       for j = 1:length(matchingTerminals)
           equipments{length(equipments) + 1} = findEquipmentByTerminal(matchingTerminals{j}, transformerWindings, generators, loads, lines);
       end
       connectEquipments(mdl, equipments);
    end
    
    new_mdl = 'model_complete';
    save_system(mdl,new_mdl);    
end

function matchingTerminals = getTerminals(connectivityNode, allTerminals)
    matchingTerminals = {};
    for i = 1:length(allTerminals)
        terminal = allTerminals(i);
        if strcmp(connectivityNode.ATTRIBUTE(1).ID, terminal.Terminal_ConnectivityNode.ATTRIBUTE(1).rdf_resource)
            matchingTerminals{length(matchingTerminals) + 1} = terminal;
        end
    end
end

function equipment = findEquipmentByTerminal(terminal, allTransformers, allGenerators, allLoads, allLines)
    referenceId = terminal.Terminal_ConductingEquipment.ATTRIBUTE(1).rdf_resource;
    for i = 1:length(allTransformers)
        if strcmp(referenceId, allTransformers(i).ATTRIBUTE(1).ID)
            equipment = allTransformers(i);
            return
        end
    end
    for i = 1:length(allGenerators)
        if strcmp(referenceId, allGenerators(i).ATTRIBUTE(1).ID)
            equipment = allGenerators(i);
            return
        end
    end
    for i = 1:length(allLoads)
        if strcmp(referenceId, allLoads(i).ATTRIBUTE(1).ID)
            equipment = allLoads(i);
            return
        end
    end
    for i = 1:length(allLines)
        if strcmp(referenceId, allLines(i).ATTRIBUTE(1).ID)
            equipment = allLines(i);
            return
        end
    end
end

function connectEquipments(mdl, equipments)
    % sufficient to connect one equipment with each other equipment
    for i = 2:length(equipments)
            connect(mdl, equipments{1,1}, equipments{1,i});
    end
end

function connect(mdl, fromEquipment, toEquipment)
    fprintf('Connect\n');
    disp(fromEquipment);
    fprintf('with\n');
    disp(toEquipment);
    
    fromHandles = getAppropriateHandles(fromEquipment);
    toHandles = getAppropriateHandles(toEquipment);
    
    for i=1:3
        add_line(mdl,fromHandles(i),toHandles(i));
    end
end

function transformer = getWindingTransformer(transformerWinding, transformers)
    for i = 1:length(transformers)
        if strcmp(transformers(i).ATTRIBUTE(1).ID, transformerWinding.TransformerWinding_PowerTransformer.ATTRIBUTE(1).rdf_resource)
            transformer = transformers(i);
            return
        end
    end
end

function handles = getAppropriateHandles(equipment)
    phs = get(equipment.block,'Porthandles');
    if strcmp(equipment.type, 'transformerWinding')
        transformerWinding = equipment;
        if isempty(strfind(transformerWinding.TransformerWinding_windingType.ATTRIBUTE(1).rdf_resource, 'primary'))
            handles = phs.LConn;
        else
            handles = phs.RConn;
        end
    elseif strcmp(equipment.type, 'generator')
        handles = phs.RConn;
    elseif strcmp(equipment.type, 'load')
        handles = phs.LConn;
    elseif strcmp(equipment.type, 'line')
        line = equipment;
        pc = get_param(line.block,'PortConnectivity');
        if and(isempty(pc(1).SrcBlock),isempty(pc(1).DstBlock))
            handles = phs.LConn;
        else
            handles = phs.RConn;
        end
    else
        error('Could not find appropriate port handles for equipment %s', equipment.IdentifiedObject_name);
    end
end
%fprintf('%s\n', var.ID);
