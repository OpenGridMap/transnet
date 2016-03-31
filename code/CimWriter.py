
from CIM14.ENTSOE.Equipment.Core import *
from CIM14.ENTSOE.Equipment.Wires import *
from CIM14.ENTSOE.Equipment.Generation.Production import *

from PyCIM import cimwrite
from PyCIM.PrettyPrintXML import xmlpp

import uuid
import collections


class CimWriter:
    circuits = None
    winding_types = ['primary', 'secondary', 'tertiary']

    base_voltages_dict = dict()
    base_voltages_dict[110000] = BaseVoltage(nominalVoltage=110000)
    base_voltages_dict[220000] = BaseVoltage(nominalVoltage=220000)
    base_voltages_dict[380000] = BaseVoltage(nominalVoltage=380000)

    region = SubGeographicalRegion(Region=GeographicalRegion(name='Germany'))

    # osm id -> cim uuid
    uuid_by_osmid_dict = dict()
    # cim uuid -> cim object
    cimobject_by_uuid_dict = dict()
    # cim uuid -> cim connectivity node object
    connectivity_by_uuid_dict = dict()

    def __init__(self, circuits):
        self.circuits = circuits

    def publish(self, file_name):

        for circuit in self.circuits:
            station1 = circuit.members[0]
            station2 = circuit.members[len(circuit.members) - 1]
            line_length = self.line_length(circuit)

            if 'station' in station1.type:
                connectivity_node1 = self.substation_to_cim(station1, circuit.voltage)
            elif 'plant' in station1.type or 'generator' in station1.type:
                connectivity_node1 = self.generator_to_cim(station1)
            else:
                print 'Invalid circuit! - Skip circuit'
                circuit.print_circuit()
                continue

            if 'station' in station2.type:
                connectivity_node2 = self.substation_to_cim(station2, circuit.voltage)
            elif 'plant' in station2.type or 'generator' in station2.type:
                connectivity_node2 = self.generator_to_cim(station2)
            else:
                print 'Invalid circuit! - Skip circuit'
                circuit.print_circuit()
                continue

            self.line_to_cim(connectivity_node1, connectivity_node2, line_length, circuit.name, circuit.voltage)

        #d_vals=sorted(dictionary.values())
        #d_keys= sorted(dictionary, key=dictionary.get)
        #dictionary = collections.OrderedDict(zip(d_keys, d_vals))

        cimwrite(self.cimobject_by_uuid_dict, file_name)

        #print '\nWhat is in path:\n'
        #print xmlpp(file_name)

    def substation_to_cim(self, osm_substation, circuit_voltage):
        transformer_winding = None
        if self.uuid_by_osmid_dict.has_key(osm_substation.id):
            print 'Substation with OSMID ' + str(osm_substation.id) + ' already covered.'
            cim_substation = self.cimobject_by_uuid_dict[self.uuid_by_osmid_dict[osm_substation.id]]
            transformer = cim_substation.getEquipments()[0] # TODO check if there is actually one equipment
            for winding in transformer.getTransformerWindings():
                if int(circuit_voltage) == winding.ratedU:
                    print 'Transformer of Substation with OSMID ' + str(osm_substation.id) + ' already has winding for voltage ' + circuit_voltage
                    transformer_winding = winding
                    break
        else:
            print 'Create CIM Substation for OSMID ' + str(osm_substation.id)
            cim_substation = Substation(name=osm_substation.name, Region=self.region)
            transformer = PowerTransformer(name=cim_substation.name, EquipmentContainer=cim_substation)
            cim_substation.UUID = str(uuid.uuid1())
            transformer.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[cim_substation.UUID] = cim_substation
            self.cimobject_by_uuid_dict[transformer.UUID] = transformer
            self.uuid_by_osmid_dict[osm_substation.id] = cim_substation.UUID
        if transformer_winding is None:
            transformer_winding = TransformerWinding(b=0, x=1.0, r=1.0, connectionType='Yn',
                                                     windingType=self.get_winding_type(osm_substation, circuit_voltage),
                                                     ratedU=int(circuit_voltage), ratedS=5000000,
                                                     PowerTransformer=transformer,
                                                     BaseVoltage=self.base_voltages_dict[int(circuit_voltage)])
            transformer_winding.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[transformer_winding.UUID] = transformer_winding
            connectivity_node = ConnectivityNode(name='conn1')
            connectivity_node.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[connectivity_node.UUID] = connectivity_node
            terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=transformer_winding,
                            sequenceNumber=1)
            terminal.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[terminal.UUID] = terminal
            self.connectivity_by_uuid_dict[transformer_winding.UUID] = connectivity_node
        return self.connectivity_by_uuid_dict[transformer_winding.UUID]

    def generator_to_cim(self, generator):
        if self.uuid_by_osmid_dict.has_key(generator.id):
            print 'Generator with OSMID ' + str(generator.id) + ' already covered.'
            generating_unit = self.cimobject_by_uuid_dict[self.uuid_by_osmid_dict[generator.id]]
        else:
            print 'Create CIM Generator for OSMID ' + str(generator.id)
            generating_unit = GeneratingUnit(name=generator.name, maxOperatingP=generator.nominal_power, minOperatingP=0,
                                             nominalP=generator.nominal_power)
            synchronous_machine = SynchronousMachine(name=generator.name, operatingMode='generator', qPercent=0, x=0.01,
                                                     r=0.01, ratedS=generator.nominal_power, type='generator',
                                                     GeneratingUnit=generating_unit)
            generating_unit.UUID = str(uuid.uuid1())
            synchronous_machine.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[generating_unit.UUID] = generating_unit
            self.cimobject_by_uuid_dict[synchronous_machine.UUID] = synchronous_machine
            self.uuid_by_osmid_dict[generator.id] = generating_unit.UUID
            connectivity_node = ConnectivityNode(name='conn1')
            connectivity_node.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[connectivity_node.UUID] = connectivity_node
            terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=synchronous_machine,
                                sequenceNumber=1)
            terminal.UUID = str(uuid.uuid1())
            self.cimobject_by_uuid_dict[terminal.UUID] = terminal
            self.connectivity_by_uuid_dict[generating_unit.UUID] = connectivity_node
        return self.connectivity_by_uuid_dict[generating_unit.UUID]

    def line_to_cim(self, connectivity_node1, connectivity_node2, length, name, circuit_voltage):
        line = ACLineSegment(name=name, bch=0, r=0.3257, x=0.3153, r0=0.5336,
                             x0=0.88025, length=length, BaseVoltage=self.base_voltages_dict[int(circuit_voltage)])
        line.UUID = str(uuid.uuid1())
        self.cimobject_by_uuid_dict[line.UUID] = line
        terminal1 = Terminal(ConnectivityNode=connectivity_node1, ConductingEquipment=line, sequenceNumber=1)
        terminal1.UUID = str(uuid.uuid1())
        self.cimobject_by_uuid_dict[terminal1.UUID] = terminal1
        terminal2 = Terminal(ConnectivityNode=connectivity_node2, ConductingEquipment=line, sequenceNumber=2)
        terminal2.UUID = str(uuid.uuid1())
        self.cimobject_by_uuid_dict[terminal2.UUID] = terminal2

    def get_winding_type(self, substation, circuit_voltage):
        separator = ','
        if separator not in substation.voltage:
            separator = ';'
        i = 0
        for station_voltage in substation.voltage.split(separator):
            if station_voltage == circuit_voltage:
                return self.winding_types[i]
            i += 1
        return None

    def line_length(self, circuit):
        line_length = 0
        for line_part in circuit.members[1:(len(circuit.members) - 2)]:
            line_length += line_part.length()
        return line_length