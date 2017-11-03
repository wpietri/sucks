import base64
import re
import sys

# a script to take an xmpppeek log of a Ecovacs app session with a Deebot N79 and strip out some of the nonsense,
# including any private identifiers

source_ip = None
userid = None
resourceid = None
robotid = None
auth_glob = None

for line in sys.stdin:
    # remove the garbage
    line = line.rstrip()
    line = re.sub("\[\\d{4}-\\d{2}-\\d{2} ", '', line)
    line = re.sub("\.\\d{6}-\\d{2}:\\d{2}\] \[", ' ', line)
    line = re.sub("]$", ' ', line)
    line = re.sub("\(([SC])2[SC]\) [.0-9]+:\\d+ -> [.0-9]+:\d+\]", '\\1', line)
    line = re.sub("\}\}\}", '', line)
    line = re.sub("\{\{\{", '', line)

    # find the private bits and remove them
    if not source_ip:
        match = re.search('Client connect from ([.0-9]+)', line)
        if match:
            source_ip = match.group(1)
    if not userid:
        match = re.search('(20\d{6}[0-9a-f]{13})@ecouser.net/([0-9a-f]{8})', line)
        if match:
            userid = match.group(1)
            resourceid = match.group(2)
    if not robotid:
        match = re.search('(E\d{8,})@126.ecorobot.net/atom', line)
        if match:
            robotid = match.group(1)
    if not auth_glob:
        match = re.search('<auth mechanism="PLAIN" xmlns="urn:ietf:params:xml:ns:xmpp-sasl">([-A-Za-z0-9+/=]+)</auth>',
                          line)
        if match:
            auth_glob = match.group(1)
    if source_ip:
        line = re.sub(source_ip, 'SOURCEIP', line)
    if userid:
        line = re.sub(userid, 'USERID', line)
    if resourceid:
        line = re.sub(resourceid, 'RESOURCEID', line)
    if robotid:
        line = re.sub(robotid, 'ROBOTID', line)
    if auth_glob:
        line = re.sub(auth_glob, 'AUTHGLOB', line)

    # translate client commmands

    line = re.sub(
        '<iq id="(\d+)" to="ROBOTID@126.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl">(<ctl .*>)</query></iq>',
        'id=\\1 command=\\2', line)

    # translate server responses

    line = re.sub(
        '<iq to="USERID@ecouser.net/RESOURCEID" type="result" id="(\d+)" from="ROBOTID@126.ecorobot.net/atom"/>',
        'id=\\1 result =empty', line)
    line = re.sub(
        '<iq to="USERID@ecouser.net/RESOURCEID" type="set" id="(\d+)" from="ROBOTID@126.ecorobot.net/atom"><query xmlns="com:ctl"><ctl id="(\d+)" ret="([^"]+)"/></query></iq>',
        'id=\\1 id=\\2 result=\\3', line)
    line = re.sub(
        '<iq to="USERID@ecouser.net/RESOURCEID" type="set" id="(\d+)" from="ROBOTID@126.ecorobot.net/atom"><query xmlns="com:ctl">(<ctl .*)</query></iq>',
        'id=\\1 response=\\2', line)

    print(line)

# per SASL plain auth: https://tools.ietf.org/html/rfc4616
(authentication_id, authorization_id, password) = base64.b64decode(auth_glob).decode().split(sep='\0')

# no idea what the leading field is, and the resource appears to be the same
(mystery, resource, secret) = password.split('/')

print("------------------")
print("sample config:")
print("user=" + userid)
print("domain=ecouser.net")
print("resource=" + resourceid)
print("secret=" + secret)
print("vacuum=" + robotid + "@126.ecorobot.net")
