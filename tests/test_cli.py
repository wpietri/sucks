import requests_mock
from nose.tools import *

from sucks.cli import *


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


def test_continent_for_country():
    assert_equal(continent_for_country('us'), 'na')
    assert_equal(continent_for_country('fr'), 'eu')


def test_wrap_command():
    v = VacBot('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12',
               {"did": "E0000000001234567890", "class": "126", "nick": "bob"}, 'na')
    c = str(v.wrap_command(Clean(1).to_xml()))
    assert_true(re.search(r'from="20170101abcdefabcdefa@ecouser.net/abcdef12"', c))
    assert_true(re.search(r'to="E0000000001234567890@126.ecorobot.net/atom"', c))


def test_model_variation():
    v = VacBot('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12',
               {"did": "E0000000001234567890", "class": "141", "nick": "bob"}, 'na')
    c = str(v.wrap_command(Clean(1).to_xml()))
    assert_true(re.search(r'to="E0000000001234567890@141.ecorobot.net/atom"', c))


def test_main_api_setup():
    with requests_mock.mock() as m:
        r1 = m.get(re.compile('user/login'),
                   text='{"time": 1511200804243, "data": {"accessToken": "7a375650b0b1efd780029284479c4e41", "uid": "2017102559f0ee63c588d", "username": null, "email": "william-ecovacs@pota.to", "country": "us"}, "code": "0000", "msg": "X"}')
        r2 = m.get(re.compile('user/getAuthCode'),
                   text='{"time": 1511200804607, "data": {"authCode": "5c28dac1ff580210e11292df57e87bef"}, "code": "0000", "msg": "X"}')
        r3 = m.post(re.compile('user.do'),
                    text='{"todo": "result", "token": "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s", "result": "ok", "userId": "2017102559f0ee63c588d", "resource": "f8d99c4d"}')
        EcoVacsAPI("long_device_id", "account_id", "password_hash", 'us', 'na')
        assert_equals(r1.call_count, 1)
        assert_equals(r2.call_count, 1)
        assert_equals(r3.call_count, 1)


def test_device_lookup():
    api = make_api()
    with requests_mock.mock() as m:
        device_id = 'E0000001234567890123'

        r = m.post(re.compile('user.do'),
                   text='{"todo": "result", "devices": [{"did": "%s", "class": "126", "nick": "bob"}], "result": "ok"}' % device_id)
        d = api.devices()
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        vacuum = d[0]
        assert_equals(vacuum['did'], device_id)
        assert_equals(vacuum['class'], '126')


def make_api():
    with requests_mock.mock() as m:
        m.get(re.compile('user/login'),
              text='{"time": 1511200804243, "data": {"accessToken": "0123456789abcdef0123456789abcdef", "uid": "20170101abcdefabcdefa", "username": null, "email": "username@example.com", "country": "us"}, "code": "0000", "msg": "X"}')
        m.get(re.compile('user/getAuthCode'),
              text='{"time": 1511200804607, "data": {"authCode": "abcdef01234567890abcdef012345678"}, "code": "0000", "msg": "X"}')
        m.post(re.compile('user.do'),
               text='{"todo": "result", "token": "base64base64base64base64base64ba", "result": "ok", "userId": "20170101abcdefabcdefa", "resource": "abcdef12"}')
        return EcoVacsAPI("long_device_id", "account_id", "password_hash", 'us', 'na')
