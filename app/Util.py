class Util:
    @staticmethod
    def have_common_voltage(vstring1, vstring2):
        if vstring1 is None or vstring2 is None:
            return True
        for v1 in vstring1.split(';'):
            for v2 in vstring2.split(';'):
                if v1.strip() == v2.strip():
                    return True
        return False
