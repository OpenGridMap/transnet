import io
import logging
import re
import uuid
from collections import OrderedDict
from string import maketrans
from xml.dom.minidom import parse
import ast

import ogr
import osr
from CIM14.ENTSOE.Equipment.Core import BaseVoltage, GeographicalRegion, SubGeographicalRegion, ConnectivityNode, \
    Terminal
from CIM14.ENTSOE.Equipment.LoadModel import LoadResponseCharacteristic
from CIM14.ENTSOE.Equipment.Wires import PowerTransformer, SynchronousMachine, TransformerWinding
from CIM14.IEC61968.Common import Location, PositionPoint
from CIM14.IEC61970.Core import Substation
from CIM14.IEC61970.Generation.Production import GeneratingUnit
from CIM14.IEC61970.Wires import ACLineSegment, EnergyConsumer
from PyCIM import cimwrite
from shapely.ops import linemerge

from LoadEstimator import LoadEstimator
from CSVWriter import CSVWriter


class CimWriter:
    circuits = None
    centroid = None
    population_by_station_dict = ()
    voltage_levels = None
    id = 0
    winding_types = ['primary', 'secondary', 'tertiary']
    root = logging.getLogger()
    base_voltages_dict = dict()

    region = SubGeographicalRegion(Region=GeographicalRegion(name='EU'))

    # osm id -> cim uuid
    uuid_by_osmid_dict = dict()
    # cim uuid -> cim object
    cimobject_by_uuid_dict = OrderedDict()
    # cim uuid -> cim connectivity node object
    connectivity_by_uuid_dict = dict()

    def __init__(self, circuits, centroid, population_by_station_dict, voltage_levels, country_name, count_substations):
        self.circuits = circuits
        self.centroid = centroid
        self.population_by_station_dict = population_by_station_dict
        self.voltage_levels = voltage_levels
        self.base_voltages_dict = dict()
        self.uuid_by_osmid_dict = dict()
        self.cimobject_by_uuid_dict = OrderedDict()
        self.connectivity_by_uuid_dict = dict()
        self.country_name = country_name
        self.count_substations = count_substations
        self.root = logging.getLogger()

    def publish(self, file_name):
        self.region.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[self.region.UUID] = self.region

        self.add_location(self.centroid.x, self.centroid.y, is_center=True)

        total_line_length = 0
        voltages = set()
        cables = set()
        wires = set()
        types = set()
        line_length = 0

        for circuit in self.circuits:
            station1 = circuit.members[0]
            station2 = circuit.members[-1]

            try:
                for line_part in circuit.members[1:-1]:
                    tags_list = ast.literal_eval(str(line_part.tags))
                    line_tags = dict(zip(tags_list[::2], tags_list[1::2]))
                    line_tags_keys = line_tags.keys()
                    voltages.update([CSVWriter.try_parse_int(v) for v in line_part.voltage.split(';')])
                    if 'cables' in line_tags_keys:
                        cables.update([CSVWriter.try_parse_int(line_tags['cables'])])
                    if 'wires' in line_tags_keys:
                        wires.update(
                            CSVWriter.convert_wire_names_to_numbers(CSVWriter.sanitize_csv(line_tags['wires'])))
                    types.update([line_part.type])

                    line_length += line_part.length
            except Exception as ex:
                print('Error line_to_cim_param_extraction')

            if 'station' in station1.type:
                connectivity_node1 = self.substation_to_cim(station1, circuit.voltage)
            elif 'plant' in station1.type or 'generator' in station1.type:
                connectivity_node1 = self.generator_to_cim(station1, circuit.voltage)
            else:
                self.root.error('Invalid circuit! - Skip circuit')
                circuit.print_circuit()
                continue

            if 'station' in station2.type:
                connectivity_node2 = self.substation_to_cim(station2, circuit.voltage)
            elif 'plant' in station2.type or 'generator' in station2.type:
                connectivity_node2 = self.generator_to_cim(station2, circuit.voltage)
            else:
                self.root.error('Invalid circuit! - Skip circuit')
                circuit.print_circuit()
                continue

            lines_wsg84 = []
            line_length = 0
            for line_wsg84 in circuit.members[1:-1]:
                lines_wsg84.append(line_wsg84.geom)
                line_length += line_wsg84.length
            line_wsg84 = linemerge(lines_wsg84)
            total_line_length += line_length
            self.root.debug('Map line from (%lf,%lf) to (%lf,%lf) with length %s meters', station1.geom.centroid.y,
                            station1.geom.centroid.x, station2.geom.centroid.y, station2.geom.centroid.x,
                            str(line_length))
            self.line_to_cim(connectivity_node1, connectivity_node2, line_length, circuit.name, circuit.voltage,
                             line_wsg84.centroid.y, line_wsg84.centroid.x, line_length, cables, voltages, wires)

            # self.root.info('The inferred net\'s length is %s meters', str(total_line_length))

        self.attach_loads()

        cimwrite(self.cimobject_by_uuid_dict, file_name + '.xml', encoding='utf-8')
        cimwrite(self.cimobject_by_uuid_dict, file_name + '.rdf', encoding='utf-8')

        # pretty print cim file
        xml = parse(file_name + '.xml')
        pretty_xml_as_string = xml.toprettyxml(encoding='utf-8')
        matches = re.findall('#x[0-9a-f]{4}', pretty_xml_as_string)
        for match in matches:
            pretty_xml_as_string = pretty_xml_as_string.replace(match, unichr(int(match[2:len(match)], 16)))
        pretty_file = io.open(file_name + '_pretty.xml', 'w', encoding='utf8')
        pretty_file.write(unicode(pretty_xml_as_string))
        pretty_file.close()

    def substation_to_cim(self, osm_substation, circuit_voltage):
        transformer_winding = None
        if osm_substation.id in self.uuid_by_osmid_dict:
            self.root.debug('Substation with OSMID %s already covered', str(osm_substation.id))
            cim_substation = self.cimobject_by_uuid_dict[self.uuid_by_osmid_dict[osm_substation.id]]
            transformer = cim_substation.getEquipments()[0]  # TODO check if there is actually one equipment
            for winding in transformer.getTransformerWindings():
                if int(circuit_voltage) == winding.ratedU:
                    self.root.debug('Transformer of Substation with OSMID %s already has winding for voltage %s',
                                    str(osm_substation.id), circuit_voltage)
                    transformer_winding = winding
                    break
        else:
            self.root.debug('Create CIM Substation for OSMID %s', str(osm_substation.id))
            cim_substation = Substation(name='SS_' + str(osm_substation.id), Region=self.region,
                                        Location=self.add_location(osm_substation.lat, osm_substation.lon))
            transformer = PowerTransformer(name='T_' + str(osm_substation.id) + '_' + CimWriter.escape_string(
                osm_substation.voltage) + '_' + CimWriter.escape_string(osm_substation.name),
                                           EquipmentContainer=cim_substation)
            cim_substation.UUID = str(CimWriter.uuid())
            transformer.UUID = str(CimWriter.uuid())
            self.cimobject_by_uuid_dict[cim_substation.UUID] = cim_substation
            self.cimobject_by_uuid_dict[transformer.UUID] = transformer
            self.uuid_by_osmid_dict[osm_substation.id] = cim_substation.UUID
        if transformer_winding is None:
            transformer_winding = self.add_transformer_winding(osm_substation.id, int(circuit_voltage), transformer)
        return self.connectivity_by_uuid_dict[transformer_winding.UUID]

    def generator_to_cim(self, generator, circuit_voltage):
        if generator.id in self.uuid_by_osmid_dict:
            self.root.debug('Generator with OSMID %s already covered', str(generator.id))
            generating_unit = self.cimobject_by_uuid_dict[self.uuid_by_osmid_dict[generator.id]]
        else:
            self.root.debug('Create CIM Generator for OSMID %s', str(generator.id))
            generating_unit = GeneratingUnit(name='G_' + str(generator.id), maxOperatingP=generator.nominal_power,
                                             minOperatingP=0,
                                             nominalP=generator.nominal_power if generator.nominal_power else '',
                                             Location=self.add_location(generator.lat, generator.lon))
            synchronous_machine = SynchronousMachine(
                name='G_' + str(generator.id) + '_' + CimWriter.escape_string(generator.name),
                operatingMode='generator', qPercent=0, x=0.01,
                r=0.01, ratedS='' if generator.nominal_power is None else generator.nominal_power, type='generator',
                GeneratingUnit=generating_unit, BaseVoltage=self.base_voltage(int(circuit_voltage)))
            generating_unit.UUID = str(CimWriter.uuid())
            synchronous_machine.UUID = str(CimWriter.uuid())
            self.cimobject_by_uuid_dict[generating_unit.UUID] = generating_unit
            self.cimobject_by_uuid_dict[synchronous_machine.UUID] = synchronous_machine
            self.uuid_by_osmid_dict[generator.id] = generating_unit.UUID
            connectivity_node = ConnectivityNode(name='CN_' + str(generator.id) + '_' + circuit_voltage)
            connectivity_node.UUID = str(CimWriter.uuid())
            self.cimobject_by_uuid_dict[connectivity_node.UUID] = connectivity_node
            terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=synchronous_machine,
                                sequenceNumber=1)
            terminal.UUID = str(CimWriter.uuid())
            self.cimobject_by_uuid_dict[terminal.UUID] = terminal
            self.connectivity_by_uuid_dict[generating_unit.UUID] = connectivity_node
        return self.connectivity_by_uuid_dict[generating_unit.UUID]

    def line_to_cim(self, connectivity_node1, connectivity_node2, length, name, circuit_voltage, lat, lon, line_length
                    , cables, voltages, wires):

        r = 0.3257
        x = 0.3153
        # r0 = 0.5336
        # x0 = 0.88025

        r0 = 0
        x0 = 0

        coeffs_of_voltage = {
            220000: dict(wires_typical=2.0, r=0.08, x=0.32, c=11.5, i=1.3),
            380000: dict(wires_typical=4.0, r=0.025, x=0.25, c=13.7, i=2.6)
        }

        length_selected = round(line_length)
        cables_selected = CSVWriter.convert_max_set_to_string(cables)
        voltage_selected = CSVWriter.convert_max_set_to_string(voltages)
        wires_selected = CSVWriter.convert_max_set_to_string(wires)

        voltage_selected_round = 0
        if 360000 <= int(voltage_selected) <= 400000:
            voltage_selected_round = 380000
        elif 180000 <= int(voltage_selected) <= 260000:
            voltage_selected_round = 220000
        try:
            if length_selected and cables_selected and int(
                    voltage_selected_round) in coeffs_of_voltage and wires_selected:
                coeffs = coeffs_of_voltage[int(voltage_selected_round)]
                # Specific resistance of the transmission lines.
                if coeffs['wires_typical']:
                    r = coeffs['r'] / (int(wires_selected) / coeffs['wires_typical']) / (
                            int(cables_selected) / 3.0)
                    # Specific reactance of the transmission lines.
                    x = coeffs['x'] / (int(wires_selected) / coeffs['wires_typical']) / (
                            int(cables_selected) / 3.0)
        except Exception as ex:
            print('Error line_to_cim')

        line = ACLineSegment(
            name=CimWriter.escape_string(name) + '_' + connectivity_node1.name + '_' + connectivity_node2.name, bch=0,
            r=r, x=x, r0=r0, x0=x0, length=length, BaseVoltage=self.base_voltage(int(circuit_voltage)),
            Location=self.add_location(lat, lon))
        line.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[line.UUID] = line
        terminal1 = Terminal(ConnectivityNode=connectivity_node1, ConductingEquipment=line, sequenceNumber=1)
        terminal1.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[terminal1.UUID] = terminal1
        terminal2 = Terminal(ConnectivityNode=connectivity_node2, ConductingEquipment=line, sequenceNumber=2)
        terminal2.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[terminal2.UUID] = terminal2

    @staticmethod
    def uuid():
        return uuid.uuid1()

    def increase_winding_type(self, winding):
        index = 0
        for winding_type in self.winding_types:
            if winding_type == winding.windingType:
                winding.windingType = self.winding_types[index + 1]
                break
            index += 1

    def add_transformer_winding(self, osm_substation_id, winding_voltage, transformer):
        new_transformer_winding = TransformerWinding(name='TW_' + str(osm_substation_id) + '_' + str(winding_voltage),
                                                     b=0, x=1.0, r=1.0, connectionType='Yn',
                                                     ratedU=winding_voltage, ratedS=5000000,
                                                     BaseVoltage=self.base_voltage(winding_voltage))
        # init with primary
        index = 0
        for winding in transformer.getTransformerWindings():
            # already a primary winding with at least as high voltage as the new one
            if winding.ratedU >= winding_voltage:
                index += 1
            else:
                self.increase_winding_type(winding)
        new_transformer_winding.windingType = self.winding_types[index]
        new_transformer_winding.setPowerTransformer(transformer)
        new_transformer_winding.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[new_transformer_winding.UUID] = new_transformer_winding
        connectivity_node = ConnectivityNode(name='CN_' + str(osm_substation_id) + '_' + str(winding_voltage))
        connectivity_node.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[connectivity_node.UUID] = connectivity_node
        terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=new_transformer_winding,
                            sequenceNumber=1)
        terminal.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[terminal.UUID] = terminal
        self.connectivity_by_uuid_dict[new_transformer_winding.UUID] = connectivity_node
        return new_transformer_winding

    def attach_loads(self):
        for load in self.cimobject_by_uuid_dict.values():
            if isinstance(load, PowerTransformer):
                transformer = load
                osm_substation_id = transformer.name.split('_')[1]
                # self.root.info('Attach load to substation %s', osm_substation_id)
                transformer_lower_voltage = CimWriter.determine_load_voltage(transformer)
                self.attach_load(osm_substation_id, transformer_lower_voltage, transformer)

    @staticmethod
    def determine_load_voltage(transformer):
        transformer_lower_voltage = transformer.getTransformerWindings()[0].ratedU
        for winding in transformer.getTransformerWindings():
            transformer_lower_voltage = winding.ratedU if winding.ratedU < transformer_lower_voltage \
                else transformer_lower_voltage
        return transformer_lower_voltage

    def attach_load(self, osm_substation_id, winding_voltage, transformer):
        transformer_winding = None
        if len(transformer.getTransformerWindings()) >= 2:
            for winding in transformer.getTransformerWindings():
                if winding_voltage == winding.ratedU:
                    transformer_winding = winding
                    break
        # add winding for lower voltage, if not already existing or
        # add winding if sub-station is a switching station (only one voltage level)
        if transformer_winding is None:
            transformer_winding = self.add_transformer_winding(osm_substation_id, winding_voltage, transformer)
        connectivity_node = self.connectivity_by_uuid_dict[transformer_winding.UUID]
        estimated_load = LoadEstimator.estimate_load(self.population_by_station_dict[str(
            osm_substation_id)]) if self.population_by_station_dict is not None else LoadEstimator.estimate_load_country(
            self.country_name, self.count_substations)
        load_response_characteristic = LoadResponseCharacteristic(exponentModel=False, pConstantPower=estimated_load)
        load_response_characteristic.UUID = str(CimWriter.uuid())
        energy_consumer = EnergyConsumer(name='L_' + osm_substation_id, LoadResponse=load_response_characteristic,
                                         BaseVoltage=self.base_voltage(winding_voltage))
        energy_consumer.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[load_response_characteristic.UUID] = load_response_characteristic
        self.cimobject_by_uuid_dict[energy_consumer.UUID] = energy_consumer
        terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=energy_consumer,
                            sequenceNumber=1)
        terminal.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[terminal.UUID] = terminal

    @staticmethod
    def escape_string(string):
        if string is not None:
            string = unicode(string.translate(maketrans('-]^$/. ', '_______')), 'utf-8')
            hexstr = ''
            for c in string:
                if ord(c) > 127:
                    hexstr += "#x%04x" % ord(c)
                else:
                    hexstr += c
            return hexstr
        return ''

    def add_location(self, lat, lon, is_center=False):
        pp = PositionPoint(yPosition=lat, xPosition=lon)
        if is_center:
            pp.zPosition = 1
        pp.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[pp.UUID] = pp
        location = Location(PositionPoints=[pp])
        location.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[location.UUID] = location
        return location

    @staticmethod
    def convert_mercator_to_wgs84(merc_lat, merc_lon):
        # Spatial Reference System
        input_epsg = 3857
        output_epsg = 4326

        # create a geometry from coordinates
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(merc_lon, merc_lat)

        # create coordinate transformation
        in_spatial_ref = osr.SpatialReference()
        in_spatial_ref.ImportFromEPSG(input_epsg)

        out_spatial_ref = osr.SpatialReference()
        out_spatial_ref.ImportFromEPSG(output_epsg)

        coord_transform = osr.CoordinateTransformation(in_spatial_ref, in_spatial_ref)

        # transform point
        point.Transform(coord_transform)

        # return point in EPSG 4326
        return point.GetY(), point.GetX()

    def base_voltage(self, voltage):
        if voltage in self.base_voltages_dict:
            return self.base_voltages_dict[voltage]
        base_voltage = BaseVoltage(nominalVoltage=voltage)
        base_voltage.UUID = str(CimWriter.uuid())
        self.cimobject_by_uuid_dict[base_voltage.UUID] = base_voltage
        self.base_voltages_dict[voltage] = base_voltage
        return base_voltage
