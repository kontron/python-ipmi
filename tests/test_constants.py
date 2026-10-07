from pyipmi.constants import manufacturer_name


def test_manufacturer_name():
    assert manufacturer_name(11) == 'Hewlett-Packard'
    assert manufacturer_name(0x0012a2) == 'VITA'
    assert manufacturer_name(0x00315a) == 'PICMG'
    assert manufacturer_name(15000) == 'Kontron'
    assert manufacturer_name(12345) is None
