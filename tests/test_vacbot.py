from nose.tools import *

from sucks import *



def test_handle_clean_report():
    v = a_vacbot()
    assert_equals(None, v.clean_status)

    v._handle_ctl({'event': 'clean_report', 'type': 'auto', 'speed': 'strong'})
    assert_equals('auto', v.clean_status)


def test_handle_charge_state():
    v = a_vacbot()
    assert_equals(None, v.clean_status)

    v._handle_ctl({'event': 'charge_state', 'type': 'going'})
    assert_equals('returning', v.charge_status)

    v._handle_ctl({'event': 'charge_state', 'type': 'slot_charging'})
    assert_equals('charging', v.charge_status)

    v._handle_ctl({'event': 'charge_state', 'type': 'idle'})
    assert_equals('idle', v.charge_status)


def test_handle_battery_info():
    v = a_vacbot()
    assert_equals(None, v.battery_status)

    v._handle_ctl({'event': 'battery_info', 'power': '100'})
    assert_equals(1.0, v.battery_status)

    v._handle_ctl({'event': 'battery_info', 'power': '095'})
    assert_equals(0.95, v.battery_status)

    v._handle_ctl({'event': 'battery_info', 'power': '000'})
    assert_equals(0.0, v.battery_status)


def test_handle_unknown_ctl():
    v = a_vacbot()
    v._handle_ctl({'event': 'weird_and_unknown_event', 'type': 'pretty_weird'})
    # as long as it doesn't blow up, that's fine


# as-yet unhandled messages:
#
# <ctl td="LifeSpan" type="Brush" val="099" total="365"/>
# <ctl td="LifeSpan" type="DustCaseHeap" val="098" total="365"/>
# <ctl td="LifeSpan" type="SideBrush" val="098" total="365"/>
# <ctl td="Sched2"/>
# <ctl td="Sched2" id="30800321"/>
#
# plus errors!

def test_bot_address():
    v = a_vacbot(bot={"did": "E0000000001234567890", "class": "126", "nick": "bob"})
    assert_equals('E0000000001234567890@126.ecorobot.net/atom', v._vacuum_address())


def test_model_variation():
    v = a_vacbot(bot={"did": "E0000000001234567890", "class": "141", "nick": "bob"})
    assert_equals('E0000000001234567890@141.ecorobot.net/atom', v._vacuum_address())



def a_vacbot(bot=None):
    if bot is None:
        bot = {"did": "E0000000001234567890", "class": "126", "nick": "bob"}
    return VacBot('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12',
                  bot, 'na')
