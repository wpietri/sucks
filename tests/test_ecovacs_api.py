from re import compile

import requests_mock
from nose.tools import *

from sucks import *


def test_md5():
    assert_equal(EcoVacsAPI.md5("fnord"), "b15e400c8dbd6697f26385216d32a40f")


def test_encrypt():
    assert_equal(len(EcoVacsAPI.encrypt("fnord")), 172)


def test_main_api_setup():
    with requests_mock.mock() as m:
        r1 = m.get(compile('user/login'),
                   text='{"time": 1511200804243, "data": {"accessToken": "7a375650b0b1efd780029284479c4e41", "uid": "2017102559f0ee63c588d", "username": null, "email": "william-ecovacs@pota.to", "country": "us"}, "code": "0000", "msg": "X"}')
        r2 = m.get(compile('user/getAuthCode'),
                   text='{"time": 1511200804607, "data": {"authCode": "5c28dac1ff580210e11292df57e87bef"}, "code": "0000", "msg": "X"}')
        r3 = m.post(compile('user.do'),
                    text='{"todo": "result", "token": "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s", "result": "ok", "userId": "2017102559f0ee63c588d", "resource": "f8d99c4d"}')

        api = EcoVacsAPI("long_device_id", "account_id", "password_hash", 'us', 'na')

        # verify setup
        assert_equals(api.resource, "long_dev")

        # verify calls
        assert_equals(r1.call_count, 1)
        assert_equals(r2.call_count, 1)
        assert_equals(r3.call_count, 1)

        # verify state
        assert_equals(api.uid, "2017102559f0ee63c588d")
        assert_equals(api.login_access_token, "7a375650b0b1efd780029284479c4e41")
        assert_equals(api.auth_code, "5c28dac1ff580210e11292df57e87bef")
        assert_equals(api.user_access_token, "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s")

        #Test old user api endpoint
        postdata = {'country': 'US',
                'resource': "f8d99c4d",
                'realm': EcoVacsAPI.REALM,
                'userId': "2017102559f0ee63c588d",
                'token': "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s"}

        r = api._EcoVacsAPI__call_user_api("loginByItToken",  postdata)
        assert_equals(r3.call_count, 2)
        # verify state
        assert_equals(api.uid, "2017102559f0ee63c588d")
        assert_equals(api.login_access_token, "7a375650b0b1efd780029284479c4e41")
        assert_equals(api.auth_code, "5c28dac1ff580210e11292df57e87bef")
        assert_equals(api.user_access_token, "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s")
        



def test_main_api_setup_with_alternate_uid():
    # Under mysterious circumstances, for certain people the last call sometimes returns a different userId
    # along with the user access token. If that's the case, we should use that as the UID for future calls

    with requests_mock.mock() as m:
        r1 = m.get(compile('user/login'),
                   text='{"time": 1511200804243, "data": {"accessToken": "7a375650b0b1efd780029284479c4e41", "uid": "2017102559f0ee63c588d", "username": null, "email": "william-ecovacs@pota.to", "country": "us"}, "code": "0000", "msg": "X"}')
        r2 = m.get(compile('user/getAuthCode'),
                   text='{"time": 1511200804607, "data": {"authCode": "5c28dac1ff580210e11292df57e87bef"}, "code": "0000", "msg": "X"}')
        r3 = m.post(compile('user.do'),
                    text='{"todo": "result", "token": "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s", "result": "ok", "userId": "abcdef", "resource": "f8d99c4d"}')

        api = EcoVacsAPI("long_device_id", "account_id", "password_hash", 'us', 'na')

        assert_equals(r1.call_count, 1)
        assert_equals(r2.call_count, 1)
        assert_equals(r3.call_count, 1)

        # verify state
        assert_equals(api.uid, "abcdef")
        assert_equals(api.login_access_token, "7a375650b0b1efd780029284479c4e41")
        assert_equals(api.auth_code, "5c28dac1ff580210e11292df57e87bef")
        assert_equals(api.user_access_token, "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s")

def test_main_api_errorcode():
    with requests_mock.mock() as m:
        r1 = m.get(compile('user/login'), #test with 0004 (invalid token)
                   text='{"time": 1511200804243, "code": "0004", "msg": "X", "data": null}')
       
        assert_raises(RuntimeError, EcoVacsAPI, "long_device_id", "account_id", "password_hash", 'us', 'na') #Runtime error from code 0004
                

def test_main_api_badpassword():
    with requests_mock.mock() as m:
        r1 = m.get(compile('user/login'), #test with 1005 (incorrect email or password)
                   text='{"time": 1511200804243, "code": "1005", "msg": "X", "data": null}')
       
        assert_raises(ValueError, EcoVacsAPI, "long_device_id", "account_id", "password_hash", 'us', 'na') #ValueError error from code 1005


def test_device_lookup():
    api = make_api()
    with requests_mock.mock() as m:

        #Not IOTMQ
        device_id = 'E0000001234567890123'
        device_class = '126'
        device_company = 'eco-legacy'
        r = m.post(compile('user.do'),
                text='{"todo": "result", "devices": [{"did": "%s", "company": "%s", "class": "%s", "nick": "bob"}], "result": "ok"}' %(device_id, device_company, device_class))
    
        d = api.devices()
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        vacuum = d[0]
        assert_equals(vacuum['did'], device_id)
        assert_equals(vacuum['class'], '126')
        assert_equals(vacuum['iotmq'], False)

        #Is IOTMQ
        device_class = 'ls1ok3' #D900
        device_company = 'eco-ng'
        r = m.post(compile('user.do'),
                text='{"todo": "result", "devices": [{"did": "%s", "company": "%s", "class": "%s", "nick": "bob"}], "result": "ok"}' %(device_id, device_company, device_class))

        d = api.devices()
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        vacuum = d[0]
        assert_equals(vacuum['did'], device_id)
        assert_equals(vacuum['class'], device_class)
        assert_equals(vacuum['iotmq'], True)


def test_device_lookup_IOTProduct():
    api = make_api()
    with requests_mock.mock() as m:

        #Is IOTProduct
        device_id = 'E0000001234567890123'
        device_class = 'ls1ok3' #D900
        device_company = 'eco-ng'

        r = m.post(compile('user.do'),
                text='{"todo": "result", "devices": [{"did": "%s", "company": "%s", "class": "%s", "nick": "bob"}], "result": "ok"}' %(device_id, device_company, device_class))
        r = m.post(compile('pim/product/getProductIotMap'),
                text='{"code":0,"data":[{"classid":"dl8fht","product":{"_id":"5acb0fa87c295c0001876ecf","name":"DEEBOT 600 Series","icon":"5acc32067c295c0001876eea","UILogicId":"dl8fht","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5acc32067c295c0001876eea"}},{"classid":"02uwxm","product":{"_id":"5ae1481e7ccd1a0001e1f69e","name":"DEEBOT OZMO Slim10 Series","icon":"5b1dddc48bc45700014035a1","UILogicId":"02uwxm","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b1dddc48bc45700014035a1"}},{"classid":"y79a7u","product":{"_id":"5b04c0227ccd1a0001e1f6a8","name":"DEEBOT OZMO 900","icon":"5b04c0217ccd1a0001e1f6a7","UILogicId":"y79a7u","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b04c0217ccd1a0001e1f6a7"}},{"classid":"jr3pqa","product":{"_id":"5b43077b8bc457000140363e","name":"DEEBOT 711","icon":"5b5ac4cc8d5a56000111e769","UILogicId":"jr3pqa","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4cc8d5a56000111e769"}},{"classid":"uv242z","product":{"_id":"5b5149b4ac0b87000148c128","name":"DEEBOT 710","icon":"5b5ac4e45f21100001882bb9","UILogicId":"uv242z","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4e45f21100001882bb9"}},{"classid":"ls1ok3","product":{"_id":"5b6561060506b100015c8868","name":"DEEBOT 900 Series","icon":"5ba4a2cb6c2f120001c32839","UILogicId":"ls1ok3","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5ba4a2cb6c2f120001c32839"}}]}')
                          
        d = api.devices()
        d = api.SetIOTDevices(d, api.getiotProducts())
        
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        vacuum = d[0]
        assert_equals(vacuum['did'], device_id)
        assert_equals(vacuum['class'], device_class)
        assert_equals(vacuum['iot_product'], True)
        assert_equals(vacuum['iotmq'], True)       

        #Not IOTProduct
        device_id = 'E0000001234567890123'
        device_class = '126'
        device_company = 'eco-legacy'

        r = m.post(compile('user.do'),
                text='{"todo": "result", "devices": [{"did": "%s", "company": "%s", "class": "%s", "nick": "bob"}], "result": "ok"}' %(device_id, device_company, device_class))
        r = m.post(compile('pim/product/getProductIotMap'),
                text='{"code":0,"data":[{"classid":"dl8fht","product":{"_id":"5acb0fa87c295c0001876ecf","name":"DEEBOT 600 Series","icon":"5acc32067c295c0001876eea","UILogicId":"dl8fht","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5acc32067c295c0001876eea"}},{"classid":"02uwxm","product":{"_id":"5ae1481e7ccd1a0001e1f69e","name":"DEEBOT OZMO Slim10 Series","icon":"5b1dddc48bc45700014035a1","UILogicId":"02uwxm","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b1dddc48bc45700014035a1"}},{"classid":"y79a7u","product":{"_id":"5b04c0227ccd1a0001e1f6a8","name":"DEEBOT OZMO 900","icon":"5b04c0217ccd1a0001e1f6a7","UILogicId":"y79a7u","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b04c0217ccd1a0001e1f6a7"}},{"classid":"jr3pqa","product":{"_id":"5b43077b8bc457000140363e","name":"DEEBOT 711","icon":"5b5ac4cc8d5a56000111e769","UILogicId":"jr3pqa","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4cc8d5a56000111e769"}},{"classid":"uv242z","product":{"_id":"5b5149b4ac0b87000148c128","name":"DEEBOT 710","icon":"5b5ac4e45f21100001882bb9","UILogicId":"uv242z","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4e45f21100001882bb9"}},{"classid":"ls1ok3","product":{"_id":"5b6561060506b100015c8868","name":"DEEBOT 900 Series","icon":"5ba4a2cb6c2f120001c32839","UILogicId":"ls1ok3","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5ba4a2cb6c2f120001c32839"}}]}')
                          
        d = api.devices()
        d = api.SetIOTDevices(d, api.getiotProducts())
        
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        vacuum = d[0]
        assert_equals(vacuum['did'], device_id)
        assert_equals(vacuum['class'], device_class)
        assert_equals(vacuum['iot_product'], False)
        assert_equals(vacuum['iotmq'], False)   

def make_api():
    with requests_mock.mock() as m:
        m.get(compile('user/login'),
              text='{"time": 1511200804243, "data": {"accessToken": "0123456789abcdef0123456789abcdef", "uid": "20170101abcdefabcdefa", "username": null, "email": "username@example.com", "country": "us"}, "code": "0000", "msg": "X"}')
        m.get(compile('user/getAuthCode'),
              text='{"time": 1511200804607, "data": {"authCode": "abcdef01234567890abcdef012345678"}, "code": "0000", "msg": "X"}')
        m.post(compile('user.do'),
              text='{"todo": "result", "token": "base64base64base64base64base64ba", "result": "ok", "userId": "20170101abcdefabcdefa", "resource": "abcdef12"}')
        m.post(compile('pim/product/getProductIotMap'),
              text='{"code":0,"data":[{"classid":"dl8fht","product":{"_id":"5acb0fa87c295c0001876ecf","name":"DEEBOT 600 Series","icon":"5acc32067c295c0001876eea","UILogicId":"dl8fht","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5acc32067c295c0001876eea"}},{"classid":"02uwxm","product":{"_id":"5ae1481e7ccd1a0001e1f69e","name":"DEEBOT OZMO Slim10 Series","icon":"5b1dddc48bc45700014035a1","UILogicId":"02uwxm","ota":false,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b1dddc48bc45700014035a1"}},{"classid":"y79a7u","product":{"_id":"5b04c0227ccd1a0001e1f6a8","name":"DEEBOT OZMO 900","icon":"5b04c0217ccd1a0001e1f6a7","UILogicId":"y79a7u","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b04c0217ccd1a0001e1f6a7"}},{"classid":"jr3pqa","product":{"_id":"5b43077b8bc457000140363e","name":"DEEBOT 711","icon":"5b5ac4cc8d5a56000111e769","UILogicId":"jr3pqa","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4cc8d5a56000111e769"}},{"classid":"uv242z","product":{"_id":"5b5149b4ac0b87000148c128","name":"DEEBOT 710","icon":"5b5ac4e45f21100001882bb9","UILogicId":"uv242z","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5b5ac4e45f21100001882bb9"}},{"classid":"ls1ok3","product":{"_id":"5b6561060506b100015c8868","name":"DEEBOT 900 Series","icon":"5ba4a2cb6c2f120001c32839","UILogicId":"ls1ok3","ota":true,"iconUrl":"https://portal-ww.ecouser.net/api/pim/file/get/5ba4a2cb6c2f120001c32839"}}]}')
        return EcoVacsAPI("long_device_id", "account_id", "password_hash", 'us', 'na')
