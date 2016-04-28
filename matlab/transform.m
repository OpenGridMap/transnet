function transform()

    % simplify cim model to be better readable by MATLAB
    system('sh preparsescript.sh /home/lej/PycharmProjects/transnet/results/cim_pretty.xml matcim.xml')

    % reed cim objects
    [tree, ~] = xml_read ('matcim.xml');
    baseVoltages = tree(1).BaseVoltage;
    transformers = tree(1).PowerTransformer;
    substations = tree(1).Substation;
    transformerWindings = tree(1).TransformerWinding;
    connectivityNodes = tree(1).ConnectivityNode;
    terminals = tree(1).Terminal;
    lines = tree(1).ACLineSegment;
    generators = tree(1).SynchronousMachine;
    generatingUnits = tree(1).GeneratingUnit;
    loads = tree(1).EnergyConsumer;
    locations = tree(1).Location;
    positionPoints = tree(1).PositionPoint;

    mdl = 'model';
    close_system('model');
    open(mdl);

    blocks = {};
    for i = 1:length(transformers)
       block = add_block('block_templates/transformer',[mdl,'/',transformers(i).IdentifiedObject_name]);
       transformers(i).type = 'transformer';
       substation_index = findSubstationByTransformer(substations, transformers(i));
       positionPoint = findPositionPoint(positionPoints, locations, substations(substation_index));
       setLatLonPosition(block, positionPoint.PositionPoint_yPosition, positionPoint.PositionPoint_xPosition);
       transformers(i).block = block;
       substations(substation_index).block = block;
       blocks{length(blocks) + 1} = block;
    end
    
    for i = 1:length(transformerWindings)
       transformerWindings(i).type = 'transformerWinding';
       transformer = findWindingTransformer(transformerWindings(i), transformers);
       parameter = 'Winding1';
       if ~isPrimaryWinding(transformerWindings(i)) 
           parameter = 'Winding2';
       end
       set_param(transformer.block, parameter, ['[',getBaseVoltage(baseVoltages, transformerWindings(i).ConductingEquipment_BaseVoltage.ATTRIBUTE(1).rdf_resource),',0.002,0.08]'])
       transformerWindings(i).block = transformer.block;
    end
    
    for i = 1:length(generators)
       block = add_block('block_templates/generator',[mdl,'/',generators(i).IdentifiedObject_name]);
       generators(i).type = 'generator';
       set_param(block, 'Voltage', getBaseVoltage(baseVoltages, generators(i).ConductingEquipment_BaseVoltage.ATTRIBUTE(1).rdf_resource));
       positionPoint = findPositionPoint(positionPoints, locations, findGeneratingUnit(generatingUnits, generators(i)));
       setLatLonPosition(block, positionPoint.PositionPoint_yPosition, positionPoint.PositionPoint_xPosition);
       generators(i).block = block;
       blocks{length(blocks) + 1} = block;
    end
    
    for i = 1:length(loads)
       block = add_block('block_templates/load',[mdl,'/',loads(i).IdentifiedObject_name]);
       loads(i).type = 'load';
       set_param(block, 'NominalVoltage', getBaseVoltage(baseVoltages, loads(i).ConductingEquipment_BaseVoltage.ATTRIBUTE(1).rdf_resource));
       loads(i).block = block;
       loads(i).substation = findSubstationByLoad(substations, loads(i));
       blocks{length(blocks) + 1} = block;
    end
    
    for i = 1:length(lines)
       block = add_block('block_templates/line',[mdl,'/',lines(i).IdentifiedObject_name]);
       lines(i).type = 'line';
       set_param(block, 'Length', num2str(lines(i).Conductor_length/1000)); % in km
       positionPoint = findPositionPoint(positionPoints, locations, lines(i));
       setLatLonPosition(block, positionPoint.PositionPoint_yPosition, positionPoint.PositionPoint_xPosition);
       lines(i).block = block;
       blocks{length(blocks) + 1} = block;
    end
    
    for i = 1:length(connectivityNodes)
       equipments = {};
       matchingTerminals = getTerminals(connectivityNodes(i), terminals);
       for j = 1:length(matchingTerminals)
           equipments{length(equipments) + 1} = findEquipmentByTerminal(matchingTerminals{j}, transformerWindings, generators, loads, lines);
       end
       connectEquipments(mdl, equipments);
       addBus(mdl, equipments{1}, equipments{2}, getBaseVoltage(baseVoltages, equipments{1}.ConductingEquipment_BaseVoltage.ATTRIBUTE(1).rdf_resource), num2str(i));  
    end
    
    set_param(mdl, 'ZoomFactor', 'FitSystem');
    % find left bottom corner
    position = get_param(blocks{i}, 'Position');
    minX = position(1);
    minY = position(4);
    for i = 2:length(blocks)
        position = get_param(blocks{i}, 'Position');
        left = position(1);
        bottom = position(4);
        if left < minX
            minX = left;
        end
        if bottom < minY
            minY = bottom;
        end
    end
    
    %modelLocation = get_param(gcs,'location');
    block = add_block('block_templates/powergui',[mdl,'/powergui']);
    setXYPosition(block, minX, minY *(-1));
    
    new_mdl = 'model_complete';
    save_system(mdl,new_mdl);    
end

function addBus(mdl, fromEquipment, toEquipment, voltage, busNo)
    block = add_block('block_templates/Load Flow Bus',[mdl,'/bus',busNo]);
    set_param(block, 'Vbase', voltage);
    set_param(block, 'ID', ['bus',busNo])
    fromEquipmentPosition = get_param(fromEquipment.block, 'Position');
    toEquipmentPosition = get_param(toEquipment.block, 'Position');
    fromEquipmentName = get_param(fromEquipment.block, 'Name');
    xdiff = abs(toEquipmentPosition(1) - fromEquipmentPosition(1));
    ydiff = abs(toEquipmentPosition(2) - fromEquipmentPosition(2));
    if xdiff > ydiff
        busXPosition = fromEquipmentPosition(1) + abs(toEquipmentPosition(1) - fromEquipmentPosition(1));
        busYPosition = fromEquipmentPosition(2) + 100;
    else
        busYPosition = fromEquipmentPosition(2) + abs(toEquipmentPosition(2) - fromEquipmentPosition(2));
        busXPosition = fromEquipmentPosition(1) + 100;
    end
    fprintf('Creating load flow bus%s at equipment %s (x=%f,y=%f)\n', busNo, fromEquipmentName, busXPosition, busYPosition);
    setXYPosition(block, busXPosition, (-1) * busYPosition);
    equipmentHandles = getAppropriateHandles(fromEquipment);
    busHandles = get(block,'Porthandles');
    add_line(mdl, equipmentHandles(3), busHandles.LConn(1));
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
    fprintf('Connect %s with %s\n', fromEquipment.IdentifiedObject_name, toEquipment.IdentifiedObject_name);
    
    if strcmp(toEquipment.type, 'load')
       setLoadPositionAndOrientation(toEquipment, toEquipment.substation);
    else
       setOrientation(fromEquipment, toEquipment); 
    end
    
    fromHandles = getAppropriateHandles(fromEquipment);
    toHandles = getAppropriateHandles(toEquipment);
    
    for i=1:3
        add_line(mdl,fromHandles(i),toHandles(i));
    end
end

function transformer = findWindingTransformer(transformerWinding, transformers)
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
        if isPrimaryWinding(transformerWinding)
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

function voltage = getBaseVoltage(baseVoltages, baseVoltageId)
    for i = 1:length(baseVoltages)
        if strcmp(baseVoltages(i).ATTRIBUTE(1).ID, baseVoltageId)
            voltage = int2str(baseVoltages(i).BaseVoltage_nominalVoltage);
            return
        end
    end
end

function isPrimary = isPrimaryWinding(transformerWinding)
    isPrimary = ~isempty(strfind(transformerWinding.TransformerWinding_windingType.ATTRIBUTE(1).rdf_resource, 'primary'));
end

function positionPoint = findPositionPoint(positionPoints, locations, equipment)
    for i = 1:length(locations)
        if strcmp(locations(i).ATTRIBUTE(1).ID, equipment.PowerSystemResource_Location.ATTRIBUTE(1).rdf_resource)
            for j = 1:length(positionPoints)
                if strcmp(locations(i).ATTRIBUTE(1).ID, positionPoints(j).PositionPoint_Location.ATTRIBUTE(1).rdf_resource)
                    positionPoint = positionPoints(j);
                    return
                end
            end
        end
    end
end

function generatingUnit = findGeneratingUnit(generatingUnits, generator)
    for i = 1:length(generatingUnits)
        if strcmp(generatingUnits(i).ATTRIBUTE(1).ID, generator.SynchronousMachine_GeneratingUnit.ATTRIBUTE(1).rdf_resource)
            generatingUnit = generatingUnits(i);
            return
        end
    end
end

function index = findSubstationByTransformer(substations, transformer)
    for i = 1:length(substations)
        if strcmp(substations(i).ATTRIBUTE(1).ID, transformer.Equipment_EquipmentContainer.ATTRIBUTE(1).rdf_resource)
            index = i;
            return
        end
    end
end

function substation = findSubstationByLoad(substations, load)
    for i = 1:length(substations)
        [~, id1] = strtok(substations(i).IdentifiedObject_name, '_');
        [~, id2] = strtok(load.IdentifiedObject_name, '_');
        if strcmp(id1, id2)
            substation = substations(i);
            return
        end
    end
end

function setLatLonPosition(block, lat, lon)
   [x,y] = Spherical2AzimuthalEquidistant((lat), (lon), 51, 9, 10000, 10000, 400000);
   setXYPosition(block, x, y);
end

function setXYPosition(block, x, y)
   name = get_param(block, 'Name');
   fprintf('Setting position of block %s to \tx=%f and y=%f\n', name, x, y);
   currentPosition = get_param(block, 'Position');
   blockWidth = currentPosition(3) - currentPosition(1);
   blockHeight = currentPosition(4) - currentPosition(2);
   currentPosition(1) = x;
   currentPosition(3) = currentPosition(1) + blockWidth;
   currentPosition(2) = y * (-1);
   currentPosition(4) = currentPosition(2) + blockHeight;
   set_param(block,'Position',currentPosition);
end

function setOrientation(fromEquipment, toEquipment)
    if strcmp(toEquipment.type, 'load')
        return
    end
    
    fromPosition = get_param(fromEquipment.block, 'Position');
    toPosition = get_param(toEquipment.block, 'Position');
    xdiff = abs(toPosition(1) - fromPosition(1));
    ydiff = abs(toPosition(2) - fromPosition(2));

    if xdiff > ydiff
        % horizontal orientation
        if fromPosition(1) > toPosition(1)
            set_param(fromEquipment.block,'Orientation','right');
        else
            set_param(fromEquipment.block,'Orientation','left');
        end
    end

    if strcmp(toEquipment.type, 'line') 
        if xdiff > ydiff
            % horizontal orientation
            if fromPosition(1) < toPosition(1)
                set_param(toEquipment.block,'Orientation','left');
            else
                set_param(toEquipment.block,'Orientation','right');
            end
        else
            % vertical orientation
            if fromPosition(2) < toPosition(2)
                set_param(toEquipment.block,'Orientation','up');
            else
                set_param(toEquipment.block,'Orientation','down');
            end
        end
    end
end

function setLoadPositionAndOrientation(load, substation)
    substationPosition = get_param(substation.block, 'Position');
    substationOrientation = get_param(substation.block, 'Orientation');
    offset = 100;
    if strcmp(substationOrientation, 'left')
       xdiff =  (-1) * offset;
       loadOrientation = 'left';
    else
       xdiff = offset; 
       loadOrientation = 'right';
    end
    setXYPosition(load.block, substationPosition(1) + xdiff, substationPosition(2) * (-1))
    set_param(load.block, 'Orientation', loadOrientation);
end