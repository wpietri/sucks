from re import compile

import requests_mock
import requests
from nose.tools import *

from sucks import *
from tests.test_ecovacs_api import make_api


# There are few tests for the IOT stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.


def test_is_iot():
    x = make_ecovacs_iot()
    assert_equal(x.vacuum['iot'], True)

def test_wrap_command():
    x = make_ecovacs_iot()
 
    c = x._wrap_command(Charge(), 'E0000000001234567890')
    assert_equal(c['cmdName'], Charge().name)
    assert_equal(c['toId'], 'E0000000001234567890')
    assert_equal(c['payload'], '<ctl><charge type="go" /></ctl>')

def test_iotapi_response():
    x = make_ecovacs_iot()
    api = make_api()
    x.api = api
    
    with requests_mock.mock() as m:
        
        #Test GetCleanState        
        resp = {"ret":"ok","resp":"<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='1159' a='15' s='0' tr=''/></ctl>","id":"Qgxa"}
        r1 = m.post(compile('iot/devmanager.do'),
            json=resp)
        cmd = VacBotCommand("GetCleanState")
        c = x._wrap_command(cmd, x.vacuum['did'])
        rtnval = api._EcoVacsAPI__call_portal_api(api.IOTDEVMANAGERAPI, '', c)        
        assert_equal(rtnval, {'ret':'ok','resp':"<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='1159' a='15' s='0' tr=''/></ctl>",'id':'Qgxa'})
                            
        #Test Timeout                
        r2 = m.post(compile('iot/devmanager.do'),exc=requests.exceptions.ReadTimeout)      
        cmd = VacBotCommand("GetCleanState")
        c = x._wrap_command(cmd, x.vacuum['did'])
        rtnval = api._EcoVacsAPI__call_portal_api(api.IOTDEVMANAGERAPI, '', c)        
        assert_equal(rtnval, {}) #Right now it sends back a blank object

def test_send_command():
    from unittest.mock import MagicMock        
    x = make_ecovacs_iot()
    x._handle_ctl = MagicMock()
    x.api._EcoVacsAPI__call_portal_api = MagicMock()
    x.send_command(Clean(iot=True), '123')


def test_subscribe_to_ctls():
    response = None

    def save_response(value):
        nonlocal response
        response = value

    x = make_ecovacs_iot()
    
    x.subscribe_to_ctls(save_response)
    message = {}
    message['resp'] = '<ctl td="CleanReport"> <clean type="auto" /> </ctl>'
    
    x.subscribe_to_ctls(save_response)
    x._handle_ctl("Clean", message)
    assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto'})


def test_xml_to_dict():
    x = make_ecovacs_iot()
    message = {}

    cmd = VacBotCommand("Clean")
    message['resp'] = "<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='1159' a='15' s='0' tr=''/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'event': 'clean_report', 'type': 'auto', 'speed': 'standard', 'st':'h','t':'1159','a':'15','s':'0','tr':''})
    
    cmd = VacBotCommand("Clean")
    message['resp'] = "<ctl ret='ok'><clean type='auto' speed='strong' st='h' t='1159' a='15' s='0' tr=''/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'event': 'clean_report', 'type': 'auto', 'speed': 'strong', 'st':'h','t':'1159','a':'15','s':'0','tr':''})

    cmd = VacBotCommand("GetBatteryInfo")
    message['resp'] = "<ctl ret='ok'><battery power='82'/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'event': 'battery_info', 'power': '82'})

    cmd = VacBotCommand("GetLifeSpan")
    message['resp'] = "<ctl ret='ok' type='Brush' left='9876' total='18000'/>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'event': 'life_span','ret':'ok', 'type': 'brush', 'left': '9876', 'total': '18000'})

    cmd = VacBotCommand("Charge")
    message['resp'] = "<ctl ts='1547823651958' td='ChargeState'><charge type='Going' h='' r='a' s='' g='0'/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'type': 'going', 'h': '', 'r': 'a', 's': '', 'g': '0', 'event': 'charge_state'}) 

    cmd = VacBotCommand("GetTestCommand")
    message['resp'] = "<ctl td='TestCommand'><test type='command'/></ctl>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'type': 'command', 'event': 'test_command'}) #Test action.name.replace Get

    cmd = VacBotCommand("Charge")
    message['resp'] = "<ctl ret='fail' errno='8'/>"
    assert_dict_equal(
        x._ctl_to_dict(cmd,message['resp']),
        {'event': 'charge_state','ret':'fail', 'errno': '8'}) #Test fail from charge command


def make_ecovacs_iot():
    eapi = make_api()
    
    with requests_mock.mock() as m:
        device_resource = 'test_resource'
        device_class = 'ls1ok3' #this is for a D900 series
        r = m.post(compile('user.do'),
                   text='{"todo": "result", "devices": [{"did": "E0000000001234567890", "class": "%s", "nick": "bob"}], "result": "ok"}' % (device_class))
        r = m.post(compile('pim/product/getProductIotMap'),
              text='{"code":0,"data":[{"classid":"dl8fht","product":{"_id":"5acb0fa87c295c0001876ecf","name":"DEEBOT 600 Series","icon":"5acc32067c295c0001876eea","UILogicId":"dl8fht","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5acc32067c295c0001876eea"}},{"classid":"02uwxm","product":{"_id":"5ae1481e7ccd1a0001e1f69e","name":"DEEBOT OZMO Slim10 Series","icon":"5b1dddc48bc45700014035a1","UILogicId":"02uwxm","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b1dddc48bc45700014035a1"}},{"classid":"y79a7u","product":{"_id":"5b04c0227ccd1a0001e1f6a8","name":"DEEBOT OZMO 900","icon":"5b04c0217ccd1a0001e1f6a7","UILogicId":"y79a7u","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b04c0217ccd1a0001e1f6a7"}},{"classid":"jr3pqa","product":{"_id":"5b43077b8bc457000140363e","name":"DEEBOT 711","icon":"5b5ac4cc8d5a56000111e769","UILogicId":"jr3pqa","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4cc8d5a56000111e769"}},{"classid":"uv242z","product":{"_id":"5b5149b4ac0b87000148c128","name":"DEEBOT 710","icon":"5b5ac4e45f21100001882bb9","UILogicId":"uv242z","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4e45f21100001882bb9"}},{"classid":"ls1ok3","product":{"_id":"5b6561060506b100015c8868","name":"DEEBOT 900 Series","icon":"5ba4a2cb6c2f120001c32839","UILogicId":"ls1ok3","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5ba4a2cb6c2f120001c32839"}}]}')
        d = eapi.devices()

    eiotvacuum = d[0]
    eiotvacuum['resource'] = device_resource
    return EcoVacsIOT('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'base64base64base64base64base64ba', 'na', eiotvacuum)