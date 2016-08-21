import unittest
from CimWriter import CimWriter
from CIM14.ENTSOE.Equipment.Wires import PowerTransformer, TransformerWinding


class CimWriterUnitTest(unittest.TestCase):
    def test_determine_load_voltage(self):
        tw1 = TransformerWinding(ratedU=380000)
        tw2 = TransformerWinding(ratedU=220000)
        tw3 = TransformerWinding(ratedU=110000)
        transformer = PowerTransformer([tw1, tw2])
        self.assertEqual(220000, CimWriter.determine_load_voltage(transformer))

        transformer = PowerTransformer([tw2])
        self.assertEqual(220000, CimWriter.determine_load_voltage(transformer))

        transformer = PowerTransformer([tw1, tw2, tw3])
        self.assertEqual(110000, CimWriter.determine_load_voltage(transformer))

    if __name__ == '__main__':
        unittest.main()
