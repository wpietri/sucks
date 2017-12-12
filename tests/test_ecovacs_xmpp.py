from re import search

from nose.tools import *

from sucks import *


# There are few tests for the XMPP stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.

def test_wrap_command():
    x = EcoVacsXMPP('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na')
    c = str(x._wrap_command(Clean(1).to_xml(), 'E0000000001234567890@126.ecorobot.net/atom'))
    assert_true(search(r'from="20170101abcdefabcdefa@ecouser.net/abcdef12"', c))
    assert_true(search(r'to="E0000000001234567890@126.ecorobot.net/atom"', c))
