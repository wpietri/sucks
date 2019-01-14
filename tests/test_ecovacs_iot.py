from re import compile

import requests_mock
from nose.tools import *

from sucks import *
from test_ecovacs_api import make_api


# There are few tests for the IOT stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.

def test_wrap_command():
    x = make_ecovacs_iot()
 
    c = x._wrap_command(Charge(), 'E0000000001234567890')
    assert_equal(c['cmdName'], Charge().name)
    assert_equal(c['toId'], 'E0000000001234567890')
    assert_equal(c['payload'], '<ctl><charge type="go" /></ctl>')

def test_is_iot():
    x = make_ecovacs_iot()


# def test_subscribe_to_ctls():
#     response = None

#     def save_response(value):
#         nonlocal response
#         response = value

#     x = make_ecovacs_iot()

#     query = x.make_iq_query()
#     query.set_payload(
#         ET.fromstring('<query xmlns="com:ctl"><ctl td="CleanReport"> <clean type="auto" /> </ctl></query>'))

#     x.subscribe_to_ctls(save_response)
#     x._handle_ctl(query)
#     assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto'})


# def test_xml_to_dict():
#     x = make_ecovacs_iot()

#     assert_dict_equal(
#         x._ctl_to_dict(make_ctl('<ctl td="CleanReport"> <clean type="auto" /> </ctl>')),
#         {'event': 'clean_report', 'type': 'auto'})
#     assert_dict_equal(
#         x._ctl_to_dict(make_ctl('<ctl td="CleanReport"> <clean type="auto" speed="strong" /> </ctl>')),
#         {'event': 'clean_report', 'type': 'auto', 'speed': 'strong'})

#     assert_dict_equal(
#         x._ctl_to_dict(make_ctl('<ctl td="BatteryInfo"><battery power="095"/></ctl>')),
#         {'event': 'battery_info', 'power': '095'})

#     assert_dict_equal(
#         x._ctl_to_dict(make_ctl('# <ctl td="LifeSpan" type="Brush" val="099" total="365"/>')),
#         {'event': 'life_span', 'type': 'brush', 'val': '099', 'total': '365'})


def make_ecovacs_iot():
    eapi = make_api()
    
    with requests_mock.mock() as m:
        device_id = 'E0000001234567890123'
        device_resource = 'test_resource'
        device_class = 'ls1ok3'
        r = m.post(compile('user.do'),
                   text='{"todo": "result", "devices": [{"did": "%s", "class": "%s", "nick": "bob"}], "result": "ok"}' % (device_id, device_class))
        r = m.post(compile('pim/product/getProductIotMap'),
              text='{"code":0,"data":[{"classid":"dl8fht","product":{"_id":"5acb0fa87c295c0001876ecf","name":"DEEBOT 600 Series","icon":"5acc32067c295c0001876eea","UILogicId":"dl8fht","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5acc32067c295c0001876eea"}},{"classid":"02uwxm","product":{"_id":"5ae1481e7ccd1a0001e1f69e","name":"DEEBOT OZMO Slim10 Series","icon":"5b1dddc48bc45700014035a1","UILogicId":"02uwxm","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b1dddc48bc45700014035a1"}},{"classid":"y79a7u","product":{"_id":"5b04c0227ccd1a0001e1f6a8","name":"DEEBOT OZMO 900","icon":"5b04c0217ccd1a0001e1f6a7","UILogicId":"y79a7u","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b04c0217ccd1a0001e1f6a7"}},{"classid":"jr3pqa","product":{"_id":"5b43077b8bc457000140363e","name":"DEEBOT 711","icon":"5b5ac4cc8d5a56000111e769","UILogicId":"jr3pqa","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4cc8d5a56000111e769"}},{"classid":"uv242z","product":{"_id":"5b5149b4ac0b87000148c128","name":"DEEBOT 710","icon":"5b5ac4e45f21100001882bb9","UILogicId":"uv242z","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4e45f21100001882bb9"}},{"classid":"ls1ok3","product":{"_id":"5b6561060506b100015c8868","name":"DEEBOT 900 Series","icon":"5ba4a2cb6c2f120001c32839","UILogicId":"ls1ok3","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5ba4a2cb6c2f120001c32839"}}]}')
        d = eapi.devices()

    eiotvacuum = d[0]
    eiotvacuum['resource'] = device_resource
    return EcoVacsIOT('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'base64base64base64base64base64ba', 'na', eiotvacuum)

def make_ctl(string):
    return ET.fromstring('<query xmlns="com:ctl">' + string + '</query>')[0]
