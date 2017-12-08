# Development resources and information for Ecovacs Robot Vacuums

For a description of the Ecovacs API protocols, see [protocol.md](protocol.md)

## MITM XMPP traffic between the Android or iOS App and the Ecovacs server

1. Download [xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html)
2. Create a certificate with the following command

`openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes`

3. Edit xmpppeek.py and change port to 5223

4. Make the App contact your machine instead of the Ecovacs server. This can be accomplished modifying your DNS server to make the Ecovacs domain point to your own IP. Another option would be to manually configure your router to re-route the traffic.

For a US user, the domain msg-na.ecouser.net should point to your local machine.

5. Run xmppeek as follows. The IP-address is the Ecovacs server

`python ./xmpppeek.py 47.88.66.164 cert.pem key.pem`