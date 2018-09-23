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



def test_device_lookup():
    api = make_api()
    with requests_mock.mock() as m:
        device_id = 'E0000001234567890123'

        r = m.post(compile('user.do'),
                   text='{"todo": "result", "devices": [{"did": "%s", "class": "126", "nick": "bob"}], "result": "ok"}' % device_id)
        d = api.devices()
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        vacuum = d[0]
        assert_equals(vacuum['did'], device_id)
        assert_equals(vacuum['class'], '126')


def make_api():
    with requests_mock.mock() as m:
        m.get(compile('user/login'),
              text='{"time": 1511200804243, "data": {"accessToken": "0123456789abcdef0123456789abcdef", "uid": "20170101abcdefabcdefa", "username": null, "email": "username@example.com", "country": "us"}, "code": "0000", "msg": "X"}')
        m.get(compile('user/getAuthCode'),
              text='{"time": 1511200804607, "data": {"authCode": "abcdef01234567890abcdef012345678"}, "code": "0000", "msg": "X"}')
        m.post(compile('user.do'),
               text='{"todo": "result", "token": "base64base64base64base64base64ba", "result": "ok", "userId": "20170101abcdefabcdefa", "resource": "abcdef12"}')
        return EcoVacsAPI("long_device_id", "account_id", "password_hash", 'us', 'na')
