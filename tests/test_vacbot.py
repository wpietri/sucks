from nose.tools import *

from sucks import *


def test_bot_address():
    v = vacbot_for_bot({"did": "E0000000001234567890", "class": "126", "nick": "bob"})
    assert_equals('E0000000001234567890@126.ecorobot.net/atom', v._vacuum_adress())


def test_model_variation():
    v = vacbot_for_bot({"did": "E0000000001234567890", "class": "141", "nick": "bob"})
    assert_equals('E0000000001234567890@141.ecorobot.net/atom', v._vacuum_adress())


def vacbot_for_bot(bot):
    return VacBot('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12',
                  bot, 'na')
