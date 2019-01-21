from re import search

from nose.tools import *

from sucks import *
import paho.mqtt

# There are few tests for the MQTT stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.

def test_subscribe_to_ctls():
    response = None

    def save_response(value):
        nonlocal response
        response = value

    x = make_ecovacs_mqtt()

    x.subscribe_to_ctls(save_response)
    test_message = paho.mqtt.client.MQTTMessage
    test_message.topic = 'iot/atr/CleanReport/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    test_message.payload = b"<ctl ts='1547824270099' td='CleanReport'><clean type='auto' speed='standard' st='h' rsn='a' a='' l='' sts=''/></ctl>"
    x._handle_ctl('','',test_message)
    
    assert_dict_equal(response, {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'standard', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})


def test_xml_to_dict():
    x = make_ecovacs_mqtt()

    test_topic = 'iot/atr/CleanReport/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547824270099' td='CleanReport'><clean type='auto' speed='standard' st='h' rsn='a' a='' l='' sts=''/></ctl>"),
        {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'standard', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})

    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547824270099' td='CleanReport'><clean type='auto' speed='strong' st='h' rsn='a' a='' l='' sts=''/></ctl>"),
        {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'strong', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})

    test_topic = 'iot/atr/BatteryInfo/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547823289924' td='BatteryInfo'><battery power='64'/></ctl>"),
        {'event': 'battery_info', 'ts':'1547823289924', 'power': '64'})

    test_topic = 'iot/atr/SleepStatus/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547823129670' td='SleepStatus' st='1'/>"),
        {'event': 'sleep_status', 'ts':'1547823129670', 'st': '1'})

    test_topic = 'iot/atr/errors/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547822982581' td='errors' old='' new='102'/>"),
        {'event': 'errors', 'ts':'1547822982581','old':'','new':'102'})
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547822982581' td='errors' old='102' new=''/>"),
        {'event': 'errors', 'ts':'1547822982581','old':'102','new':''})

    test_topic = 'iot/atr/Pos/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl td='Pos' t='p' p='7,-10' a='-42' valid='0'/>"),
        {'event': 'pos', 't':'p', 'p':'7,-10', 'a':'-42','valid':'0'})

    test_topic = 'iot/atr/DustCaseST/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547822871328' td='DustCaseST' st='1'/>"),
        {'event': 'dust_case_s_t', 'ts':'1547822871328','st':'1'})

    test_topic = 'iot/atr/MapSt/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict(test_topic, "<ctl ts='1547823592934' td='MapSt' st='relocGoChgStart' method='' info=''/>"),
        {'event': 'map_st', 'ts':'1547823592934', 'st':'reloc_go_chg_start', 'method':'', 'info':''})

    # #TODO: Find a way to check if string is b64 encoded
    # test_topic = 'iot/atr/trace/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    # assert_dict_equal(       
    #     x._ctl_to_dict(test_topic, "<ctl td='trace' trid='227975' tf='3' tt='4' tr='XQAABAAKAAAAAB4AMGAQCdAAAAA='/>"),
    #     {'event': 'trace', 'trid':'227975', 'tf':'4', 'tr':'XQAABAAKAAAAAB4AMGAQCdAAAAA='})


 
def make_ecovacs_mqtt(bot=None):
    if bot is None:
        bot = bot = {"did": "E0000000001234567890", "class": "126","resource":"test_resource", "nick": "bob", "iot": True}
    return EcoVacsMQTT('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na', bot)
