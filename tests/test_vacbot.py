from xml.etree import ElementTree

from re import search
from nose.tools import *

from sucks import *


# There are few tests for the XMPP stuff here because a) it's relatively complicated to test given
# the library's design and its multithreaded nature, and b) I'm manually testing every change anyhow,
# as it's not clear how the robot really behaves.

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


def test_wrap_command():
    v = VacBot('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12',
               {"did": "E0000000001234567890", "class": "126", "nick": "bob"}, 'na')
    c = str(v.wrap_command(Clean(1).to_xml()))
    assert_true(search(r'from="20170101abcdefabcdefa@ecouser.net/abcdef12"', c))
    assert_true(search(r'to="E0000000001234567890@126.ecorobot.net/atom"', c))


def test_model_variation():
    v = VacBot('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12',
               {"did": "E0000000001234567890", "class": "141", "nick": "bob"}, 'na')
    c = str(v.wrap_command(Clean(1).to_xml()))
    assert_true(search(r'to="E0000000001234567890@141.ecorobot.net/atom"', c))
