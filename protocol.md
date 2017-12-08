# Ecovacs Protocol

There are two protocols involved in the communication between the client and Ecovacs systems. There are a series of HTTPS requests
used to log in and find devices. Once logged in, you get a token that is
used to connect to an XMPP server, which mediates communication with the
vacuum. That's right, your robot housecleaner, like an errant teen, spends
all its free time hanging out in an internet chat room.

This is all taken from MITMing the Android app. The iOS app appears to
follow the same protocol conventions.


## Location

It appears that Ecovacs have broken up their API servers by location. Some
are designated by country, others by continent. All appear to use the
two-letter ISO codes, but at this time it doesn't look like all codes
map to valid servers.

The HTTPS and XMPP servers do not appear to be following the same convention.
For example, a Canadian user must authenticate on  country-specific HTTPS
server, but XMPP commands work both on the worldwide server 
msg-ww.ecouser.net) and the North America server (msg-na.ecouser.net)



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


The app establishes a connection to an XMPP server and logs in using
a secret that comes from the earlier HTTPS calls. It then sends XMPP IQ
commands. It describes them as queries, but they all contain "ctl"
elements that appear to be commands.



### Cleaning

**Command**
- `<ctl td="Clean"><clean type="auto" speed="standard"/></ctl>`

**State**
- **Request** `<ctl td="GetCleanState" />`
- **Response** `<ctl td="CleanReport"><clean type="stop" speed="standard" /></ctl>`
  - type `auto` automatic cleaning program
  - type `border` edge cleaning program
  - type `singleroom` cleaning a single room
  - type `stop` bot at full stop
  - speed `standard` regular fan speed (suction)
  - speed `strong` high fan speed (suction)


### Charging

**Command**
- `<query xmlns="com:ctl"><ctl td="Charge"><charge type="go"/></ctl>`
  - `go` order bot to return to charger

- *Request* `<query xmlns="com:ctl"><ctl td="GetChargeState" />`
- *Response* `<ctl td="ChargeState"><charge type="SlotCharging" /></ctl>`
  - `Idle` not trying to charge
  - `Going` trying to return to charger
  - `SlotCharging` currently charging in dock
  - `WireCharging` currently charging by cable

*Note: It appears the bot can be in an active CleanState (i.e. auto) as well as in an active ChargeState (i.e. SlotCharging). The assumption is that in this case, the cleaning task will resume after the bot is sufficiently charged. More testing is needed.*


### Battery State

Battery charge level. 080 = 80% charged.

- *Request* `<ctl td="GetBatteryInfo" />`
- *Response* `<ctl td="BatteryInfo"><battery power="080" /></ctl>` 


### Component lifespan

The remaining lifespan of components. Based on an internal counters
that can be reset with command ResetLifeSpan (untested).

It's presumed that the timers need to be reset manually.

- *Request* `<ctl td="GetLifeSpan" type="Brush" />`
- *Response* `<ctl td="LifeSpan" type="Brush" val="095" total="365" />`
  - Brush
  - SideBrush
  - DustCaseHeap


### Manually moving around

To stop the current action, issue the stop action.

**Command**
- `<ctl td="Move"><move action="forward"/></ctl>`
- `<ctl td="Move"><move action="SpinLeft"/></ctl>`
- `<ctl td="Move"><move action="SpinRight"/></ctl>`
- `<ctl td="Move"><move action="stop"/></ctl>`
- `<ctl td="Move"><move action="TurnAround"/></ctl>`



### Errors

The bot broadcasts error codes for a number of cases.

`<ctl td="error" error="BatteryLow" errno="101"></ctl>`

The latest error can be requested like so:

- **Request** `<ctl td="GetError" />`
- **Response** `<ctl ret="ok" errs="100"/>`

However in some cases the robot sends to code 100 shortly
after an error has occurred, meaning that we cannot trust
the GetError request to contain the last error.
For example, if the robot gets stuck it broadcasts 102
HostHang, thenproceeds to stop and broadcasts 100 NoError.


**Known error codes**
- 100 NoError (back to normal)
- 101 BatteryLow
- 102 HostHang (bot is stuck)
- 103 WheelAbnormal
- 104 DownSensorAbnormal



### Untested commands

```
<ctl td="GetOnOff" />
<ctl id="102461185" ret="ok" on="0"/>

<ctl id="12351409" td="PlaySound" sid="0"/>

<ctl id="13259797" td="SetTime"><time t="1509622697" tz="-7"/></ctl>

<ctl id="30800321" td="GetSched"/>

```

It appears that it adds an extra id when it cares to receive a specific response.
This is a little odd in that the iq blocks already contain ids, but perhaps one
is more a server id and the other is used by the robot itself.
