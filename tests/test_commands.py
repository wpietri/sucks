from xml.etree import ElementTree

from nose.tools import *

from sucks import *


def test_custom_command():
    # Ensure a custom-built command generates the expected XML payload
    c = VacBotCommand('CustomCommand', {'type': 'customtype'})
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="CustomCommand" type="customtype" />')


def test_custom_command_inner_tag():
    # Ensure a custom-built command generates the expected XML payload
    c = VacBotCommand('CustomCommand', {'customtag': {'customvar': 'customvalue'}})
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="CustomCommand"><customtag customvar="customvalue" /></ctl>')


def test_custom_command_noargs():
    # Ensure a custom-built command with no args generates XML without an args element
    c = VacBotCommand('CustomCommand')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="CustomCommand" />')


def test_clean_command():
    c = Clean()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="standard" type="auto" /></ctl>')  # protocol has attribs in other order
    c = Clean('edge', 'high')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="strong" type="border" /></ctl>')  # protocol has attribs in other order


def test_edge_command():
    c = Edge()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="strong" type="border" /></ctl>')  # protocol has attribs in other order


def test_spot_command():
    c = Spot()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="strong" type="spot" /></ctl>')  # protocol has attribs in other order


def test_charge_command():
    c = Charge()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Charge"><charge type="go" /></ctl>')


def test_stop_command():
    c = Stop()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="standard" type="stop" /></ctl>')


def test_get_clean_state_command():
    c = GetCleanState()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="GetCleanState" />')


def test_get_charge_state_command():
    c = GetChargeState()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="GetChargeState" />')


def test_get_battery_state_command():
    c = GetBatteryState()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="GetBatteryInfo" />')



def test_move_command():
    c = Move(action='left')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Move"><move action="SpinLeft" /></ctl>')
    c = Move(action='right')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Move"><move action="SpinRight" /></ctl>')
    c = Move(action='turn_around')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Move"><move action="TurnAround" /></ctl>')
    c = Move(action='forward')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Move"><move action="forward" /></ctl>')
    c = Move(action='stop')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Move"><move action="stop" /></ctl>')


def test_get_lifepsan_command():
    c = GetLifeSpan('main_brush')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="GetLifeSpan" type="Brush" />')
    c = GetLifeSpan('side_brush')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="GetLifeSpan" type="SideBrush" />')
    c = GetLifeSpan('filter')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="GetLifeSpan" type="DustCaseHeap" />')
