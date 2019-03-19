from re import search

from nose.tools import *

from sucks import *


# There are few tests for the XMPP stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.

def test_wrap_command():
    x = make_ecovacs_xmpp()
    c = str(x._wrap_command(Clean().to_xml(), 'E0000000001234567890@126.ecorobot.net/atom'))
    assert_true(search(r'from="20170101abcdefabcdefa@ecouser.net/abcdef12"', c))
    assert_true(search(r'to="E0000000001234567890@126.ecorobot.net/atom"', c))    
    #Convert to XML to make it easy to see if id was added to ctl
    xml_test = ET.fromstring(c)
    ctl = xml_test.getchildren()[0][0]
    assert_true(ctl.get("id")) #Check that an id was added to ctl    

    #Test if customid is added to ctl
    cwithid = Clean().to_xml()
    cwithid.attrib["id"] = "12345678" #customid 12345678
    c = str(x._wrap_command(cwithid, 'E0000000001234567890@126.ecorobot.net/atom'))    
    #Convert to XML to make it easy to see if id was added to ctl
    xml_test = ET.fromstring(c)
    ctl = xml_test.getchildren()[0][0]
    assert_equals(ctl.get("id"), "12345678") #Check that an id was added to ctl    


def test_getReqID():
    x = make_ecovacs_xmpp()
    rid = x.getReqID("12345678")
    assert_equals(rid, "12345678") #Check returned ID is the same as provided

    rid2 = x.getReqID()
    assert_true(len(rid2) >= 8) #Check returned random ID is at least 8 chars

def test_subscribe_to_ctls():
    response = None

    def save_response(value):
        nonlocal response
        response = value

    x = make_ecovacs_xmpp()

    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl td="CleanReport"> <clean type="auto" /> </ctl></query>'))

    x.subscribe_to_ctls(save_response)
    x._handle_ctl(query)
    assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto'})

def test_xml_to_dict():
    x = make_ecovacs_xmpp()

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="CleanReport"> <clean type="auto" /> </ctl>')),
        {'event': 'clean_report', 'type': 'auto'})
    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="CleanReport"> <clean type="auto" speed="strong" /> </ctl>')),
        {'event': 'clean_report', 'type': 'auto', 'speed': 'strong'})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="BatteryInfo"><battery power="095"/></ctl>')),
        {'event': 'battery_info', 'power': '095'})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('# <ctl td="LifeSpan" type="Brush" val="099" total="365"/>')),
        {'event': 'life_span', 'type': 'brush', 'val': '099', 'total': '365'})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="LifeSpan" type="DustCaseHeap" val="-050" total="365"/>')),
        {'event': 'life_span', 'type': 'dust_case_heap', 'val': '-050', 'total': '365'})
    
    assert_equals(x._ctl_to_dict(make_ctl('<ctl />')), None)


def make_ecovacs_xmpp(bot=None, server_address=None):
    if bot is None:
        bot = {"did": "E0000000001234567890", "class": "126", "nick": "bob", "iotmq": False}    
    return EcoVacsXMPP('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na', bot, server_address=server_address)

def test_xmpp_customaddress():
    x = make_ecovacs_xmpp(server_address="test.xmppserver.com")
    assert_equals(x.server_address, "test.xmppserver.com")

def make_ctl(string):
    return ET.fromstring('<query xmlns="com:ctl">' + string + '</query>')[0]
