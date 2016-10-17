class Util:
    def __init__(self):
        pass

    @staticmethod
    def have_common_voltage(vstring1, vstring2):
        if not vstring1 or not vstring2:
            return True
        for v1 in vstring1.split(';'):
            for v2 in vstring2.split(';'):
                if v1.strip() == v2.strip():
                    return True
        return False
