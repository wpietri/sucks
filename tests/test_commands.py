from xml.etree import ElementTree

from nose.tools import *

from sucks import *


def test_custom_command():
    # Ensure a custom-built command generates the expected XML payload
    c = VacBotCommand('CustomCommand', {'type': 'customtype'})
    assert_equals(ElementTree.tostring(c.to_xml()),

                  b'<ctl td="CustomCommand"><customcommand type="customtype" /></ctl>')


def test_custom_command_noargs():
    # Ensure a custom-built command with no args generates XML without an args element
    c = VacBotCommand('CustomCommand')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="CustomCommand" />')


def test_clean_command():
    c = Clean(10)
    assert_equals(c.terminal, False)
    assert_equals(c.wait, 10)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="standard" type="auto" /></ctl>')  # protocol has attribs in other order


def test_edge_command():
    # called Edge because that's what the UI uses, even though the protocol is different
    c = Edge(10)
    assert_equals(c.terminal, False)
    assert_equals(c.wait, 10)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="strong" type="border" /></ctl>')  # protocol has attribs in other order


def test_charge_command():
    c = Charge()
    assert_equals(c.terminal, True)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Charge"><charge type="go" /></ctl>')


def test_stop_command():
    c = Stop()
    assert_equals(c.terminal, True)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="standard" type="stop" /></ctl>')
