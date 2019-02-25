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


def test_custom_command_multiple_inner_tag():
    # Ensure a custom-built command with multiple inner tags generates the expected XML payload
    c = VacBotCommand('CustomCommand', {"customtag":[{"customvar":"customvalue1"},{"customvar":"customvalue2"}]})
    logging.info(ElementTree.tostring(c.to_xml()))
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="CustomCommand"><customtag customvar="customvalue1" /><customtag customvar="customvalue2" /></ctl>')

def test_custom_command_args_multiple_inner_tag():
    # Ensure a custom-built command with args and multiple inner tags generates the expected XML payload
    c = VacBotCommand('CustomCommand', {"arg1":"value1","customtag":[{"customvar":"customvalue1"},{"customvar":"customvalue2"}]})
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl arg1="value1" td="CustomCommand"><customtag customvar="customvalue1" /><customtag customvar="customvalue2" /></ctl>')


def test_custom_command_noargs():
    # Ensure a custom-built command with no args generates XML without an args element
    c = VacBotCommand('CustomCommand')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="CustomCommand" />')


def test_clean_command():
    c = Clean()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean act="s" speed="standard" type="auto" /></ctl>')  # protocol has attribs in other order
    
    c = Clean('edge', 'high')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean act="s" speed="strong" type="border" /></ctl>')  # protocol has attribs in other order

    c = Clean(iotmq=True)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean act="s" speed="standard" type="auto" /></ctl>') # test for iot act is added                         
    

def test_spotarea_command():
    assert_raises(ValueError, SpotArea, 'start') #Value error if SpotArea doesn't include a mid or p
    
    c = SpotArea('start', '0')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" mid="0" speed="standard" type="SpotArea" /></ctl>')  #Test namedarea clean

    c = SpotArea('start', area='0')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" mid="0" speed="standard" type="SpotArea" /></ctl>')  #Test namedarea keyword clean

    c = SpotArea('start', '', '-602,1812,800,723')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" deep="1" p="-602,1812,800,723" speed="standard" type="SpotArea" /></ctl>')  #Test customarea clean

    c = SpotArea('start', '', '-602,1812,800,723', '2')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" deep="2" p="-602,1812,800,723" speed="standard" type="SpotArea" /></ctl>')  #Test customarea clean with deep 2

    c = SpotArea('start', '', map_position='-602,1812,800,723')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" deep="1" p="-602,1812,800,723" speed="standard" type="SpotArea" /></ctl>')  #Test customarea keyword clean with deep default

    c = SpotArea('start', map_position='-602,1812,800,723', cleanings='2')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" deep="2" p="-602,1812,800,723" speed="standard" type="SpotArea" /></ctl>')  #Test customarea keyword and cleanings keyword clean with deep default

    c = SpotArea('start', area='0', map_position='-602,1812,800,723', cleanings='2')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" mid="0" speed="standard" type="SpotArea" /></ctl>')  #Test all keywords specified, should default to only mid

    c = SpotArea('start', '0', '-602,1812,800,723','2')
    assert_equals(ElementTree.tostring(c.to_xml()),
                b'<ctl td="Clean"><clean act="s" mid="0" speed="standard" type="SpotArea" /></ctl>')  #Test all keywords specified, should default to only mid


def test_edge_command():
    c = Edge()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean act="s" speed="strong" type="border" /></ctl>')  # protocol has attribs in other order


def test_spot_command():
    c = Spot()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean act="s" speed="strong" type="spot" /></ctl>')  # protocol has attribs in other order


def test_charge_command():
    c = Charge()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Charge"><charge type="go" /></ctl>')


def test_stop_command():
    c = Stop()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean act="s" speed="standard" type="stop" /></ctl>')


def test_play_sound_command():
    c = PlaySound()
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl sid="0" td="PlaySound" />')


def test_play_sound_command_with_sid():
    c = PlaySound(sid="1")
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl sid="1" td="PlaySound" />')


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
    c = Move(action='backward')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Move"><move action="backward" /></ctl>')
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

def test_set_time_command():
    c = SetTime('1234', 'GMT-5')
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="SetTime"><time t="1234" tz="GMT-5" /></ctl>')                  
