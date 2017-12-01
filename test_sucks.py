from xml.etree import ElementTree

import requests_mock
from nose.tools import *

from sucks import *


# There are no tests for the XMPP stuff here because a) it's relatively complicated to test given
# the library's design and its multithreaded nature, and b) I'm manually testing every change anyhow,
# as it's not clear how the robot really behaves.

def test_clean_command():
    c = Clean(10)
    assert_equals(c.terminal, False)
    assert_equals(c.wait, 10)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="standard" type="auto" /></ctl>')  # protocol has attribs in other order


def test_edge_command():
    # called Edge because that's what the UI uses, even though the protocol is different
    c = Edge(10)
    assert_equals(c.terminal, False)
    assert_equals(c.wait, 10)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="strong" type="border" /></ctl>')  # protocol has attribs in other order


def test_charge_command():
    c = Charge()
    assert_equals(c.terminal, True)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Charge"><charge type="go" /></ctl>')


def test_stop_command():
    c = Stop()
    assert_equals(c.terminal, True)
    assert_equals(ElementTree.tostring(c.to_xml()),
                  b'<ctl td="Clean"><clean speed="standard" type="stop" /></ctl>')


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


def test_main_api_called():
    with requests_mock.mock() as m:
        r1 = m.get(re.compile('user/login'),
                   text='{"time": 1511200804243, "data": {"accessToken": "7a375650b0b1efd780029284479c4e41", "uid": "2017102559f0ee63c588d", "username": null, "email": "william-ecovacs@pota.to", "country": "us"}, "code": "0000", "msg": "X"}')
        r2 = m.get(re.compile('user/getAuthCode'),
                   text='{"time": 1511200804607, "data": {"authCode": "5c28dac1ff580210e11292df57e87bef"}, "code": "0000", "msg": "X"}')
        r3 = m.post(re.compile('user.do'),
                    text='{"todo": "result", "token": "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s", "result": "ok", "userId": "2017102559f0ee63c588d", "resource": "f8d99c4d"}')
        api = EcoVacsAPI("long_device_id", "account_id", "password_hash")
        assert_equals(r1.call_count, 1)
        assert_equals(r2.call_count, 1)
        assert_equals(r3.call_count, 1)


def test_device_lookup():
    api = make_api()
    with requests_mock.mock() as m:
        device_id = 'E0000693817603910264'

        r = m.post(re.compile('user.do'),
                   text='{"todo": "result", "devices": [{"did": "%s", "class": "126", "nick": "bob"}], "result": "ok"}' % device_id)
        d = api.devices()
        assert_equals(r.call_count, 1)
        assert_equals(len(d), 1)
        assert_equals(d[0]['did'], device_id)


def make_api():
    with requests_mock.mock() as m:
        m.get(re.compile('user/login'),
              text='{"time": 1511200804243, "data": {"accessToken": "7a375650b0b1efd780029284479c4e41", "uid": "2017102559f0ee63c588d", "username": null, "email": "william-ecovacs@pota.to", "country": "us"}, "code": "0000", "msg": "X"}')
        m.get(re.compile('user/getAuthCode'),
              text='{"time": 1511200804607, "data": {"authCode": "5c28dac1ff580210e11292df57e87bef"}, "code": "0000", "msg": "X"}')
        m.post(re.compile('user.do'),
               text='{"todo": "result", "token": "jt5O7oDR3gPHdVKCeb8Czx8xw8mDXM6s", "result": "ok", "userId": "2017102559f0ee63c588d", "resource": "f8d99c4d"}')
        return EcoVacsAPI("long_device_id", "account_id", "password_hash")
