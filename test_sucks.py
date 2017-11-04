from xml.etree import ElementTree

from nose.tools import assert_equals

from sucks import *

# There are no tests for the XMPP stuff here because a) it's relatively complicated to test given
# the library's design and its multithreaded nature, and b) I'm manually testing every change anyhow,
# as it's not clear how the robot really behaves.

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

