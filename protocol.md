There are two protocols involved here. There are a series of HTTPS requests
used to log in and find devices. Once logged in, you get a token that is
used to connect to an XMPP server, which mediates communication with the
vacuum. That's right, your robot housecleaner, like an errant teen, spends
all its free time hanging out in an internet chat room.

This is all taken from MITMing the Android app. The protocol is quirky
enough that I wouldn't be shocked if the iPhone app does it differently.

## Location

It appears that Ecovacs have broken up their API servers by location. Some
are designated by country, others by continent. All appear to use the
two-letter ISO codes, but at this time it doesn't look like all codes
map to valid servers. If you're in, say, Australia and are trying to
get this to work, I'd love a packet capture of DNS requests to see what
the app does there.

## HTTPS

There are two sorts of URLs in the basic login flow. The first set use
a format like this:

```
    https://eco-{country}-api.ecovacs.com/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}
```

They also have a complicated API request signature that seems overelaborate
to me. See the Python code for more details.

1. GET eco-us-api.ecovacs.com ... common/checkVersion - appears to just check
the app version
2. GET eco-us-api.ecovacs.com ... user/login - Sends encrypted versions of
the username and password. The response is some json containing a uid and
access token.
3. GET eco-us-api.ecovacs.com ... user/getAuthCode - sends uid, accessToken;
gets back an auth code

Now we switch to posting to a different server, and the request and response
style change substantially. I think of this at the user server, or perhaps
the XMPP/device server.


4. POST users-na.ecouser.net:8000/user.do loginByItToken - trades the
authCode from the previous call for yet another token
5. POST ne-na.ecouser.net:8018/notify_engine.do - not sure what this is
for; my script skips this and seems to work fine
6. POST users-na.ecouser.net:8000/user.do GetDeviceList - Using the token
from step 4, gets the list of devices; that's needed for talking to the
vacuum via XMPP


## XMPP



The Android app establishes a connection to an XMPP server and logs in using
a secret that comes from the earlier HTTPS calls. It then sends XMPP IQ commands.
It describes
them as queries, but they all contain "ctl" elements that appear to be commands. Here are a couple of full
examples with the private information removed:


A clean command:
```
<iq id="TXID" to="ROBOTID@MODELID.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl"><ctl td="Clean"><clean type="auto" speed="standard"/></ctl></query></iq>

```

A charge command:
```
<iq id="TXID" to="ROBOTID@MODELID.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl"><ctl td="Charge"><charge type="go"/></ctl></query></iq>
```

Focusing on the core ctl elements, this is a sampling of commands seen on the wire after punching all the app buttons:

```
<ctl id="12351409" td="PlaySound" sid="0"/>
<ctl id="13259797" td="SetTime"><time t="1509622697" tz="-7"/></ctl>
<ctl id="30800321" td="GetSched"/>
<ctl td="Charge"><charge type="go"/></ctl>
<ctl td="Clean"><clean type="auto" speed="standard"/></ctl>
<ctl td="Clean"><clean type="border" speed="strong"/></ctl>
<ctl td="Clean"><clean type="singleRoom" speed="standard"/></ctl>
<ctl td="Clean"><clean type="spot" speed="strong"/></ctl>
<ctl td="Clean"><clean type="stop" speed="standard"/></ctl>
<ctl td="GetBatteryInfo"/>
<ctl td="GetChargeState"/>
<ctl td="GetCleanState"/>
<ctl td="GetLifeSpan" type="Brush"/>
<ctl td="GetLifeSpan" type="DustCaseHeap"/>
<ctl td="GetLifeSpan" type="SideBrush"/>
<ctl td="Move"><move action="forward"/></ctl>
<ctl td="Move"><move action="SpinLeft"/></ctl>
<ctl td="Move"><move action="SpinRight"/></ctl>
<ctl td="Move"><move action="stop"/></ctl>
<ctl td="Move"><move action="TurnAround"/></ctl>
```

It appears that it adds an extra id when it cares to receive a specific response. This is a little odd in that
the iq blocks already contain ids, but perhaps one is more a server id and the other is used by the robot itself.

Here are some assorted responses from that session:

```
<ctl td="BatteryInfo"><battery power="095"/></ctl>
<ctl td="ChargeState"><charge type="going"/></ctl>
<ctl td="ChargeState"><charge type="Going"/></ctl>
<ctl td="ChargeState"><charge type="Idle"/></ctl>
<ctl td="ChargeState"><charge type="SlotCharging"/></ctl>
<ctl td="CleanReport"><clean type="auto"/></ctl>
<ctl td="CleanReport"> <clean type="auto" speed="strong"/> </ctl>
<ctl td="CleanReport"><clean type="border"/></ctl>
<ctl td="CleanReport"> <clean type="border" speed="strong"/> </ctl>
<ctl td="CleanReport"><clean type="singleRoom"/></ctl>
<ctl td="CleanReport"> <clean type="singleRoom" speed="strong"/> </ctl>
<ctl td="CleanReport"><clean type="spot"/></ctl>
<ctl td="CleanReport"> <clean type="spot" speed="strong"/> </ctl>
<ctl td="CleanReport"><clean type="stop"/></ctl>
<ctl td="LifeSpan" type="Brush" val="099" total="365"/>
<ctl td="LifeSpan" type="DustCaseHeap" val="098" total="365"/>
<ctl td="LifeSpan" type="SideBrush" val="098" total="365"/>
<ctl td="Sched2"/>
<ctl td="Sched2" id="30800321"/>
```

I don't totally get the relationship between the duplicate-ish items here, like the various clean reports,
or the charge type differences, but I'll try to come back after rummaging through the logs further.
