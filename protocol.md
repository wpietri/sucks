# Ecovacs Protocol

Depending on the device there are a few different protocols involved in the communication between the client and Ecovacs systems. There are a series of HTTPS requests
used to log in and find devices. Once logged in, you get a token that is
used for connecting to different services.  In many cases this involves connecting to an XMPP server, which mediates communication with the
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

`
    https://eco-{country}-api.ecovacs.com/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}
`
 
They also have a complicated API request signature that seems overelaborate
to me. See the Python code for more details.

1. GET eco-us-api.ecovacs.com ... common/checkVersion - appears to just check
the app version
2. GET eco-us-api.ecovacs.com ... user/login - Sends encrypted versions of
the username and password. The response is some json containing a uid and
access token.
3. GET eco-us-api.ecovacs.com ... user/getAuthCode - sends uid, accessToken;
gets back an auth code

    *Under mysterious circumstances, for some people the getAuthCode call will
    return a different userId than is passed in. In that case, apparently the new userId should be used for future calls, or an Auth 1004 error results.*

Now we switch to posting to a different server, and the request and response
style change substantially. I think of this at the user server, or perhaps
the XMPP/device server.

`
   https://portal-{continent}.ecouser.net/api
`

There are a few different endpoints within the API that have been seen and are used in the library:


| Endpoint                      | Description                               |
| ----------------------------- | ----------------------------------------- |
| /users/user.do                | Handles user / account functions          |
| /iot/devmanager.do            | Handles sending commands to "IOT" devices |
| /pim/product/getProductIotMap | Provides the "IOT" Product map            |



4. POST portal-na.ecouser.net/api/users/user.do loginByItToken - trades the
authCode from the previous call for yet another token
5. POST ne-na.ecouser.net:8018/notify_engine.do - not sure what this is
for; my script skips this and seems to work fine
6. POST portal-na.ecouser.net/api/users/user.do GetDeviceList - Using the token
from step 4, gets the list of devices; that's needed for talking to the
vacuum via XMPP
7. POST
portal-na.ecouser.net/api/pim/product/getProductIotMap
getProductIotMap - Provides a list of "IOT" products, the devices are referenced in the table below and these are assumed to be "IOT" devices within the library.

    |IOT Products |
    |---|
    |DEEBOT 600 Series|
    |DEEBOT OZMO Slim10 Series |
    |DEEBOT OZMO 900|
    |DEEBOT 711|
    |DEEBOT 710|
    |DEEBOT 900 Series|



At this point depending on your device you will connect to either an XMPP server, or an MQTT server.  This is believed to be based on the "IOT Products" vs "Non-IOT" products. 

| "Non-IOT" Products                                                                | "IOT" Products                                                                                                                                                        |
|----------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Connect to an XMPP server to send commands to devices and receive status results | Connect to an MQTT server to subscribe to status messages and results.  A Rest API is utilized to send commands to devices, but can also be used to obtain statuses. |


## XMPP - ("Non-IOT")

The app establishes a connection to an XMPP server and logs in using
a secret that comes from the earlier HTTPS calls. It then sends XMPP IQ
commands. It describes them as queries, but they all contain "ctl"
elements that appear to be commands.

The Android App uses the following XMPP messaging servers:

|Country|URL|
|------|--------|
|CH|msg.ecouser.net|
|TW, MY, JP, SG, TH, HK, IN, KR|msg-as.ecouser.net|
|US|msg-na.ecouser.net|
|FR, ES, UK, NO, MX, DE, PT, CH, AU, IT, NL, SE, BE, DK|msg-eu.ecouser.net|
|Any other|msg-ww.ecouser.net|

## MQTT - ("IOT")

The app establishes a connection to an MQTT server and logs in using
a secret that comes from the earlier HTTPS calls.

It then subscribes to a topic where various status and result messages are published by the device.
The topic looks like this:

`
iot/atr/+/{deviceID}/{deviceClass}/{deviceResource}/+
`

It is believed the MQTT servers mirror the XMPP servers, but only the NA and WW have been tested so far.

|Country|URL|
|------|--------|
|US|mq-na.ecouser.net|
|"World-wide"|mq-ww.ecouser.net|

## Rest API - ("IOT")

For IOT devices the app sends commands to the device over a Rest API utilizing the secret that comes from the earlier HTTPS calls.  This API has only been tested from an "IOT" device, but could possibly work for "Non-IOT" devices as well.

The Rest API utilizes the same portal URL as used previously, but with the iot/devmanager endpoint:
`
 https://portal-{continent}.ecouser.net/api/iot/devmanager.do
`
Commands are sent via POST in the format of:
```json
{
    "auth": {
    "realm": "ecouser.net",
    "resource": "resource",
    "token": "token",
    "userid": "userid",
    "with": "users",
},
"cmdName": "cmd.name",
"payload": "cmd.args",            
"payloadType": "x",
"td": "q",
"toId": "vacuum.serial",
"toRes": "vacuum.resource",
"toType": "vacuum.class"
}   
```

### Cleaning

**Command**
- `<ctl td="Clean"><clean type="auto" speed="standard"/></ctl>`

**State**
- **Request** `<ctl td="GetCleanState" />`
- **Response** `<ctl td="CleanReport"><clean type="stop" speed="standard" /></ctl>`
  - type `auto` automatic cleaning program
  - type `border` edge cleaning program
  - type `spot` spot cleaning program
  - type `singleroom` cleaning a single room 
  - type `stop` bot at full stop
  - type `SpotArea` cleaning a mapped room
  - speed `standard` regular fan speed (suction)
  - speed `strong` high fan speed (suction)


### Charging

**Command**
- `<query xmlns="com:ctl"><ctl td="Charge"><charge type="go"/></ctl>`
  - `go` order bot to return to charger

**State**
- *Request* `<query xmlns="com:ctl"><ctl td="GetChargeState" />`
- *Response* `<ctl td="ChargeState"><charge type="SlotCharging" /></ctl>`
  - `Idle` not trying to charge
  - `Going` trying to return to charger
  - `SlotCharging` currently charging in dock
  - `WireCharging` currently charging by cable



### Battery State

Battery charge level. 080 = 80% charged. State is broadcast
continously when the robot is running och charging, but can also
be requested manually.

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

|**Command**|**Control**|
|-|-|
|Move forward|`<ctl td="Move"><move action="forward"/></ctl>`|
|Move backward|`<ctl td="Move"><move action="backward"/></ctl>`|
|Spin left 360 degrees|`<ctl td="Move"><move action="SpinLeft"/></ctl>`|
|Spin right 360 degrees|`<ctl td="Move"><move action="SpinRight"/></ctl>`|
|Turn 180 degrees|`<ctl td="Move"><move action="TurnAround"/></ctl>`|
|Stop the ongoing action|`<ctl td="Move"><move action="stop"/></ctl>`|


### Configuration

**Set/get robot internal clock**
- `<ctl td="SetTime"><time t="1509622697" tz="+8"/></ctl>`
- `<ctl td="GetTime"></ctl>`
  - Time is specified as a UNIX timestamp and timezone + or - UTC offset.

**Get firmware version**
`<ctl td="GetVersion" name="FW"/>` 

**Get robot logs**
`<ctl td="GetLog"></ctl>` 


### Errors

The bot broadcasts error codes for a number of cases.

`<ctl td="error" error="BatteryLow" errno="101"></ctl>`

The latest error can be requested like so:

- **Request** `<ctl td="GetError" />`
- **Response** `<ctl ret="ok" errs="100"/>`

However in some cases the robot sends to code 100 shortly
after an error has occurred, meaning that we cannot trust
the GetError request to contain the last relevant error.
For example, if the robot gets stuck it broadcasts 102
HostHang, then proceeds to stop and broadcasts 100 NoError.


**Known error codes**

|Code|Description|
|-----|-----|
|100|NoError: Robot is operational|
|101|BatteryLow: Low battery|
|102|HostHang: Robot is stuck|
|103|WheelAbnormal: Wheels are not moving as expected|
|104|DownSensorAbnormal: Down sensor is getting abnormal values|
|110|NoDustBox: Dust Bin Not installed|

These codes are taken from model M81 Pro. Error codes may differ
between models.

### Sounds
Different sid "Sound IDs" will play different sounds.  If the vacuum has Voice Report disabled, these won't play.
    
`<ctl td="PlaySound" sid="1" />`

|SID |Description                                               |
|-----|------------------------------------------------------------|
| 0   | Startup Music Chime                                        |
| 3   | I Am Suspended                                             |
| 4   | Check Driving Wheels                                       |
| 5   | Please Help Me Out                                         |
| 6   | Please Install Dust Bin                                    |
| 17  | Chime / Beep                                               |
| 18  | My Battery Is Low                                          |
| 29  | Please power me on before charging                         |
| 30  | I Am Here                                                  |
| 31  | Brush is tangled please clean my brush                     |
| 35  | Please clean my antidrop sensors                           |
| 48  | Brush is tangled                                           |
| 55  | I am relocating                                            |
| 56  | Upgrade succeeded                                          |
| 63  | I am returning to the charging dock                        |
| 65  | Cleaning paused                                            |
| 69  | Connected please go back to ecovacs app to continue setup  |
| 71  | I am restoring the map please do not stand beside me       |
| 73  | My battery is low returning to the charging dock           |
| 74  | Difficult to locate I am starting a new cleaning cycle     |
| 75  | I am resuming the clean                                    |
| 76  | Upgrade failed please try again                            |
| 77  | Please place me on the charging dock                       |
| 79  | Resume the clean                                           |
| 80  | I am starting the clean                                    |
| 81  | I am starting the clean                                    |
| 82  | I am starting the clean                                    |
| 84  | I am ready for mopping                                     |
| 85  | Please remove the mopping plate when I am building the map |
| 86  | Cleaning is complete returning to the charging dock        |
| 89  | LVS Malfunction please try to tap the LVS                  |
| 90  | I am upgrading please wait                                 |


### Untested commands

```
<ctl td="SetOnOff" t="b" on="1"/>
<ctl td="GetOnOff" />
<ctl id="12351409" td="PlaySound" sid="0"/>
<ctl id="30800321" td="GetSched"/>
```

It appears that it adds an extra id when it cares to receive a specific response.
This is a little odd in that the iq blocks already contain ids, but perhaps one
is more a server id and the other is used by the robot itself.
