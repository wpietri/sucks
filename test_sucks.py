from xml.etree import ElementTree

from nose.tools import *

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


def test_frequency_param_type():
    t = FREQUENCY
    assert_equals(t.convert('0', None, None), 0)
    assert_equals(t.convert('1', None, None), 1.0)
    assert_equals(t.convert('1/2', None, None), 0.5)
    assert_equals(t.convert('1/7', None, None), 1.0 / 7.0)
    assert_equals(t.convert('1/14', None, None), 1.0 / 14.0)
    assert_equals(t.convert('1/1000', None, None), 1.0 / 1000.0)
    assert_equals(t.convert('1.5/2', None, None), 1.5 / 2.0)
    assert_equals(t.convert('0/2', None, None), 0)
    with assert_raises(click.exceptions.BadParameter):
        t.convert('bob', None, None)
    with assert_raises(click.exceptions.BadParameter):
        t.convert('2', None, None)
    with assert_raises(click.exceptions.BadParameter):
        t.convert('7/5', None, None)
    with assert_raises(click.exceptions.BadParameter):
        t.convert('1/0', None, None)


def test_should_run():
    count = 0
    for _ in range(10000):
        if should_run(0.1):
            count += 1
    assert_almost_equal(count, 1000, delta=200)

    count = 0
    for _ in range(10000):
        if should_run(0.9):
            count += 1
    assert_almost_equal(count, 9000, delta=200)
