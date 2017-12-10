# Development resources and information for Ecovacs Robot Vacuums

For a description of the Ecovacs API protocols, see
[the protocol documentation](protocol.md)


## Getting started with Sucks

If you'd like to join in on developing, I recommend checking out the code,
doing `pipenv install` to set up a virtual environment, and then `pipenv shell`
to start using it. You can run the existing tests using `nosetests`. Current
test are not yet comprehensive, as the integrated nature of this makes it difficult.
But I aim to reduce that problem over time, so please add tests as you go.


## MITM XMPP traffic between the Android or iOS App and the Ecovacs server

1. Download [xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html)
2. Create a self-signed certificate with the following command

`openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes`

3. Edit xmpppeek.py and change port to 5223

4. Look at the  [the protocol documentation](protocol.md) for information on which
Ecovacs XMPP server is the right one for your Country. For example, a US user will
be using msg-na.ecouser.net. Find and note the IP address for the server.

5. Make sure the mobile App talks to your machine instead of the server. This can be
accomplished modifying your router's DNS configuration to have the Ecovacs domain
name point to your IP.

6. Run xmppeek as follows.

`python ./xmpppeek.py <ECOVACS XMPP SERVER IP> cert.pem key.pem`


## Reset robot to factory settings

Ecovacs robots have an undocumented hardware reset button that can be useful
in case you run into trouble. Under the dustbin lid there is a small round hole
that hides the button (confirmed on models M80 and M81).

With the robot on, use something thin like a paper clip or needle to press and
hold the reset button. After about three seconds the robot will beep three times
to indicate successful reset.

You will have to delete the robot from the mobile app and go through the setup
process.
