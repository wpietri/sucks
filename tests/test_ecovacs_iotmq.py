from re import search

from nose.tools import *

import requests_mock
import requests

from sucks import *
import paho.mqtt

# There are few tests for the MQTT stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.

def test_subscribe_to_ctls():
    response = None

    def save_response(value):
        nonlocal response
        response = value

    x = make_ecovacs_iotmq()
    x.subscribe_to_ctls(save_response)
    
    #Test MQTT ctl
    mqtt_message = paho.mqtt.client.MQTTMessage
    mqtt_message.topic = 'iot/atr/CleanReport/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    mqtt_message.payload = b"<ctl ts='1547824270099' td='CleanReport'><clean type='auto' speed='standard' st='h' rsn='a' a='' l='' sts=''/></ctl>"
    x._handle_ctl_mqtt('','',mqtt_message)    
    assert_dict_equal(response, {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'standard', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})

    #Test API ctl
    api_message = {}
    api_message['resp'] = '<ctl td="CleanReport"> <clean type="auto" /> </ctl>'    
    x.subscribe_to_ctls(save_response)
    x._handle_ctl_api("Clean", api_message)
    assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto'})   


def test_is_iotmq():
    x = make_ecovacs_iotmq()
    assert_equal(x.vacuum['iotmq'], True)

def test_wrap_command():
    x = make_ecovacs_iotmq()
 
    c = x._wrap_command(Charge(), 'E0000000001234567890')
    assert_equal(c['cmdName'], Charge().name)
    assert_equal(c['toId'], 'E0000000001234567890')
    assert_equal(c['payload'], '<ctl><charge type="go" /></ctl>')


def test_iotapi_response():
    x = make_ecovacs_iotmq()    
    
    with requests_mock.mock() as m:        
        url = (EcoVacsAPI.PORTAL_URL_FORMAT + "/iot/devmanager.do").format(continent=x.continent) 
        #Test GetCleanState        
        resp = {"ret":"ok","resp":"<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='1159' a='15' s='0' tr=''/></ctl>","id":"Qgxa"}
        r1 = m.post(url, json=resp)
        #r1 = m.post(compile('devmanager.do'), json=resp)
        cmd = VacBotCommand("GetCleanState")
        c = x._wrap_command(cmd, x.vacuum['did'])        
        rtnval = x._EcoVacsIOTMQ__call_iotdevmanager_api(c)
        assert_equal(rtnval, {'ret':'ok','resp':"<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='1159' a='15' s='0' tr=''/></ctl>",'id':'Qgxa'})
                            
        #Test Exception ReadTimeout                
        r2 = m.post(url, exc=requests.exceptions.ReadTimeout)
        #r2 = m.post(compile('iot/devmanager.do'),exc=requests.exceptions.ReadTimeout)      
        cmd = VacBotCommand("GetCleanState")
        c = x._wrap_command(cmd, x.vacuum['did'])
        rtnval = x._EcoVacsIOTMQ__call_iotdevmanager_api(c)        
        assert_equal(rtnval, {}) #Right now it sends back a blank object

        #Test Response Fail - Timeout                
        resp = {"ret":"fail","resp": None, "debug":"wait for response timed out" ,"id":"Qgxa"}
        r2 = m.post(url, json=resp)
        #r1 = m.post(compile('devmanager.do'), json=resp)
        cmd = VacBotCommand("TestCommand")
        c = x._wrap_command(cmd, x.vacuum['did'])        
        rtnval = x._EcoVacsIOTMQ__call_iotdevmanager_api(c)
        assert_equal(rtnval, {})

        #Test Response Fail - No debug                
        resp = {"ret":"fail","resp": None ,"id":"Qgxa"}
        r2 = m.post(url, json=resp)
        #r1 = m.post(compile('devmanager.do'), json=resp)
        cmd = VacBotCommand("TestCommand")
        c = x._wrap_command(cmd, x.vacuum['did'])        
        rtnval = x._EcoVacsIOTMQ__call_iotdevmanager_api(c)
        assert_equal(rtnval, {})

def test_send_command():
    from unittest.mock import MagicMock        
    x = make_ecovacs_iotmq()
    x._handle_ctl_api = MagicMock()
    EcoVacsIOTMQ._EcoVacsIOTMQ__call_iotdevmanager_api = MagicMock()    
    x.send_command(Clean(iotmq=True), '123')

def test_send_ping():
    from unittest.mock import MagicMock    
    x = make_ecovacs_iotmq()
    EcoVacsIOTMQ._send_simple_command = MagicMock(return_value=MQTTPublish.paho.MQTT_ERR_SUCCESS)    
    assert_true(x.send_ping()) #Test ping response success

    EcoVacsIOTMQ._send_simple_command = MagicMock(return_value=MQTTPublish.paho.MQTT_ERR_NOT_FOUND)    
    assert_false(x.send_ping()) #Test ping response fail

def test_on_connect_rc_nonzero():
    x = make_ecovacs_iotmq()
    assert_raises(RuntimeError, x.on_connect, "client", "userdata", "flags", 1)

def test_xml_to_dict_mqtt():
    x = make_ecovacs_iotmq()

    test_topic = 'iot/atr/CleanReport/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547824270099' td='CleanReport'><clean type='auto' speed='standard' st='h' rsn='a' a='' l='' sts=''/></ctl>"),
        {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'standard', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})

    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547824270099' td='CleanReport'><clean type='auto' speed='strong' st='h' rsn='a' a='' l='' sts=''/></ctl>"),
        {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'strong', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})

    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547824270099'><clean type='auto' speed='strong' st='h' rsn='a' a='' l='' sts=''/></ctl>"),
        {'event': 'clean_report', 'ts':'1547824270099','type': 'auto','speed':'strong', 'st':'h','rsn':'a', 'a':'', 'l':'', 'sts':''})      #Test without td  

    test_topic = 'iot/atr/BatteryInfo/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547823289924' td='BatteryInfo'><battery power='64'/></ctl>"),
        {'event': 'battery_info', 'ts':'1547823289924', 'power': '64'})

    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547823289924'><battery power='64'/></ctl>"),
        {'event': 'battery_info', 'ts':'1547823289924', 'power': '64'})        #Test without td

    test_topic = 'iot/atr/SleepStatus/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547823129670' td='SleepStatus' st='1'/>"),
        {'event': 'sleep_status', 'ts':'1547823129670', 'st': '1'})

    test_topic = 'iot/atr/errors/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547822982581' td='errors' old='' new='102'/>"),
        {'event': 'errors', 'ts':'1547822982581','old':'','new':'102'})
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547822982581' td='errors' old='102' new=''/>"),
        {'event': 'errors', 'ts':'1547822982581','old':'102','new':''})

    test_topic = 'iot/atr/Pos/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl td='Pos' t='p' p='7,-10' a='-42' valid='0'/>"),
        {'event': 'pos', 't':'p', 'p':'7,-10', 'a':'-42','valid':'0'})

    test_topic = 'iot/atr/DustCaseST/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547822871328' td='DustCaseST' st='1'/>"),
        {'event': 'dust_case_s_t', 'ts':'1547822871328','st':'1'})

    test_topic = 'iot/atr/MapSt/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ts='1547823592934' td='MapSt' st='relocGoChgStart' method='' info=''/>"),
        {'event': 'map_st', 'ts':'1547823592934', 'st':'reloc_go_chg_start', 'method':'', 'info':''})

    test_topic = 'iot/atr/LifeSpan/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, "<ctl ret='ok' type='Brush' left='9876' total='18000'/>"),
        {'event': 'life_span','ret':'ok', 'type': 'brush', 'left': '9876', 'total': '18000'})

    test_topic = 'iot/atr/CustomCommand/%s/%s/%s/x'.format(x.vacuum['did'], x.vacuum['class'], x.vacuum['resource'])      
    assert_dict_equal(       
        x._ctl_to_dict_mqtt(test_topic, '<ctl td="CustomCommand"><customtag customvar="customvalue1" /></ctl>'),
        {'event': 'custom_command', 'customvar': 'customvalue1'})      


def test_xml_to_dict_api():
    x = make_ecovacs_iotmq()
    message = {}

    cmd = VacBotCommand("Clean")
    message['resp'] = "<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='1159' a='15' s='0' tr=''/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'event': 'clean_report', 'type': 'auto', 'speed': 'standard', 'st':'h','t':'1159','a':'15','s':'0','tr':''})
    
    cmd = VacBotCommand("Clean")
    message['resp'] = "<ctl ret='ok'><clean type='auto' speed='strong' st='h' t='1159' a='15' s='0' tr=''/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'event': 'clean_report', 'type': 'auto', 'speed': 'strong', 'st':'h','t':'1159','a':'15','s':'0','tr':''})

    cmd = VacBotCommand("GetBatteryInfo")
    message['resp'] = "<ctl ret='ok'><battery power='82'/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'event': 'battery_info', 'power': '82'})

    cmd = VacBotCommand("GetLifeSpan")
    message['resp'] = "<ctl ret='ok' type='Brush' left='9876' total='18000'/>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'event': 'life_span','ret':'ok', 'type': 'brush', 'left': '9876', 'total': '18000'})

    cmd = VacBotCommand("Charge")
    message['resp'] = "<ctl ts='1547823651958' td='ChargeState'><charge type='Going' h='' r='a' s='' g='0'/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'type': 'going', 'h': '', 'r': 'a', 's': '', 'g': '0', 'event': 'charge_state'}) 

    cmd = VacBotCommand("GetTestCommand")
    message['resp'] = "<ctl td='TestCommand'><test type='command'/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'type': 'command', 'event': 'test_command'}) #Test action.name.replace Get

    cmd = VacBotCommand("Charge")
    message['resp'] = "<ctl ret='fail' errno='8'/>"
    assert_dict_equal(
        x._ctl_to_dict_api(cmd,message['resp']),
        {'event': 'charge_state','ret':'fail', 'errno': '8'}) #Test fail from charge command


def test_bad_port():
    bot = {"did": "E0000000001234567890", "class": "126","resource":"test_resource", "nick": "bob", "iotmq": True}
    mqtt = EcoVacsIOTMQ('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na', bot, server_address='test.com:f123')
    assert_equal(8883, mqtt.port)

def test_good_port():
    bot = {"did": "E0000000001234567890", "class": "126","resource":"test_resource", "nick": "bob", "iotmq": True}
    mqtt = EcoVacsIOTMQ('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na', bot, server_address='test.com:8000')
    assert_equal(8000, mqtt.port)    
 
def make_ecovacs_iotmq(bot=None):
    if bot is None:
        bot = {"did": "E0000000001234567890", "class": "126","resource":"test_resource", "nick": "bob", "iotmq": True}
    return EcoVacsIOTMQ('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na', bot)
