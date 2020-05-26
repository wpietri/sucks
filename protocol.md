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


| Endpoint | Description |
| - | - |
| /users/user.do | Handles user / account functions |
| /iot/devmanager.do | Provides a RestAPI that handles sending commands to "IOTMQ" devices |
| /pim/product/getProductIotMap | Provides a listing of "IOT" Products |


1. POST portal-na.ecouser.net/api/users/user.do loginByItToken - trades the
authCode from the previous call for yet another token
5. POST ne-na.ecouser.net:8018/notify_engine.do - not sure what this is
for; my script skips this and seems to work fine
6. POST portal-na.ecouser.net/api/users/user.do GetDeviceList - Using the token
from step 4, gets the list of devices; that's needed for talking to the
vacuum via XMPP
7. POST
portal-na.ecouser.net/api/pim/product/getProductIotMap
getProductIotMap - Provides a list of "IOT" products, it isn't clear what the app uses these for at this time, possibly for determining how to get updates.

At this point depending on your device you will connect to either an XMPP server, or an MQTT server.  

| "IOT XMPP" Products | "IOT MQ" Products |
| - | - |
| Connect to an XMPP server to send commands to devices and receive status results | Connect to an MQTT server to subscribe to status messages and results.  A Rest API is utilized to send commands to devices, but can also be used to obtain statuses. |


## XMPP - ("IOT XMPP")

The app establishes a connection to an XMPP server and logs in using
a secret that comes from the earlier HTTPS calls. It then sends XMPP IQ
commands. It describes them as queries, but they all contain "ctl"
elements that appear to be commands.

The Android App uses the following XMPP messaging servers:

|Country|URL|
| - | - |
|CH|msg.ecouser.net|
|TW, MY, JP, SG, TH, HK, IN, KR|msg-as.ecouser.net|
|US|msg-na.ecouser.net|
|FR, ES, UK, NO, MX, DE, PT, CH, AU, IT, NL, SE, BE, DK|msg-eu.ecouser.net|
|Any other|msg-ww.ecouser.net|

## MQTT - ("IOT MQ")

The app establishes a connection to an MQTT server and logs in using
a secret that comes from the earlier HTTPS calls.

It then subscribes to a topic where various status and result messages are published by the device.
The topic looks like this:

`
iot/atr/+/{deviceID}/{deviceClass}/{deviceResource}/+
`

It is believed the MQTT servers mirror the XMPP servers, but only the NA and WW have been tested so far.

|Country|URL|
|-|-|
|US|mq-na.ecouser.net|
|"World-wide"|mq-ww.ecouser.net|

## Rest API - ("IOT MQ")

For IOT MQ devices the app sends commands to the device over a Rest API utilizing the secret that comes from the earlier HTTPS calls.  This API has only been tested from an "IOT MQ" device, but could possibly work for other devices as well.

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

## Commands

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
  - type `SpotArea` cleaning a mapped room (mapping robots only)
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
continously when the robot is running or charging, but can also
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

#### Set/get robot internal clock
- `<ctl td="SetTime"><time t="1509622697" tz="+8"/></ctl>`
- `<ctl td="GetTime"></ctl>`
  - Time is specified as a UNIX timestamp and timezone + or - UTC offset.

#### Get firmware version
`<ctl td="GetVersion" name="FW"/>` 

#### Get robot logs
`<ctl td="GetLog"></ctl>` 

#### Get/Set option value
Gets or sets value for option (0==Off, 1==On)
##### GetOnOff
  - Do Not Disturb - `<ctl td="GetOnOff" t="b"/>`
  - Continuous Cleaning - `<ctl td="GetOnOff" t="g"/>`
  - Silence Voice Report - `<ctl td="GetOnOff" t="s"/>`

    Returns `<ctl ret='ok' on='1'/>`
##### SetOnOff
  - Do Not Disturb - `<ctl td="SetOnOff" t="b" on="0"/>`
  - Continuous Cleaning - `<ctl td="SetOnOff" t="g" on="0"/>`
  - Silence Voice Report - `<ctl td="SetOnOff" t="s" on="0"/>`

    Returns `<ctl ret='ok'/>`

#### Mopping Water Amount
Models with mopping capability (Ozmo) allow for changing the amount of water dispersed.  The value ranges from 1 (low) to 3 (high).

`<ctl td="SetWaterPermeability" v="1"/>`


#### Schedules
##### GetSched
`<ctl td="GetSched"/>`

Gets any schedules for the robot.
    
- No Schedules
  - `<ctl ret='ok'/>`
- Schedule
  - `<ctl ret='ok'><s n='FRASITLP' o='0' h='13' m='2' r='0000000' f='p'><ctl td='Clean'><clean type='auto'/></ctl></s></ctl>`

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
|-|-|
|100|NoError: Robot is operational|
|101|BatteryLow: Low battery|
|102|HostHang: Robot is off the floor|
|103|WheelAbnormal: Driving Wheel malfunction|
|104|DownSensorAbnormal: Excess dust on the Anti-Drop Sensors|
|105|Stuck: Robot is stuck|
|106|SideBrushExhausted: Side Brushes have expired|
|107|DustCaseHeapExhausted: Dust case filter expired|
|108|SideAbnormal: Side Brushes are tangled|
|109|RollAbnormal: Main Brush is tangled|
|110|NoDustBox: Dust Bin Not installed|
|111|BumpAbnormal: Bump sensor stuck|
|112|LDS: LDS "Laser Distance Sensor" malfunction|
|113|MainBrushExhausted: Main brush has expired|
|114|DustCaseFilled: Dust bin full|
|115|BatteryError: |
|116|ForwardLookingError: |
|117|GyroscopeError: |
|118|StrainerBlock: |
|119|FanError: |
|120|WaterBoxError: |
|201|AirFilterUninstall: |
|202|UltrasonicComponentAbnormal|
|203|SmallWheelError|
|UNKNOW|"unknow"|

These codes were gathered from the Android app source, but may differ
between models.

### Sounds
Different sid "Sound IDs" will play different sounds.  If the vacuum has Voice Report disabled, these won't play.  The table below was compiled by testing against a D900 series.
    
`<ctl td="PlaySound" sid="0" />`

| SID | Description |
|-|-|
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
| 89  | LDS Malfunction please try to tap the LDS                  |
| 90  | I am upgrading please wait  |

### SpotAreas
For bots with mapping capability this tells a bot to clean specified rooms.

For the CLI - the `area` command takes a csv of ints - ex `area 0,1`

You can add the option `--map-position` or `-p` to clean a specified map coordinate - ex `area -p "-602,1812,800,723"`

For the Library - you could use `vacbot.run(SpotArea('start', '0,1'))`

"0,1" is a list of mapIDs the bot should clean. Each of these corresponds to a room or area the bot mapped. In the app, these are what show the letters over rooms mapID (0) == room ("A"), (1) == "B", etc.

If you want to see your MapSet areas, you can use the library. Set --debug for sucks and then use a custom command:
`vacbot.run(VacBotCommand("GetMapSet", {"tp":"sa"}))`

You'll see in DEBUG something like:
```
sucks DEBUG got {'id': 'ralnsy', 'ret': 'ok', 'resp': "<ctl ret='ok' tp='sa' msid='11'><m mid='0' p='1'/><m mid='1' p='1'/><m mid='2' p='1'/><m mid='3' p='1'/><m mid='4' p='1'/><m mid='5' p='1'/><m mid='6' p='1'/><m mid='7' p='1'/><m mid='8' p='1'/></ctl>"}
```
This tells you I have 9 rooms mapped (mid= 0 - 8) or A-I, but you should be able to compare to the map in the app now to know which mid == what room.

#### SpotArea Friendly Names
For bots with mapping capability the app automatically names areas (rooms) A-Z.  You can rename these to "friendly names" - something the app won't let you do natively.

Use the above "GetMapSet" custom command and then convert the xml to json:
``` xml
<ctl ret='ok' tp='sa' msid='11'><m mid='0' p='1'/><m mid='1' p='1'/><m mid='2' p='1'/><m mid='3' p='1'/><m mid='4' p='1'/><m mid='5' p='1'/><m mid='6' p='1'/><m mid='7' p='1'/><m mid='8' p='1'/></ctl>
```
becomes
``` javascript
{"ctl":{"ret":"ok","tp":"sa","msid":"11","m":[{"mid":"0","p":"1"},{"mid":"1","p":"1"},{"mid":"2","p":"1"},{"mid":"3","p":"1"},{"mid":"4","p":"1"},{"mid":"5","p":"1"},{"mid":"6","p":"1"},{"mid":"7","p":"1"},{"mid":"8","p":"1"}]}}
```
Now you need to add a "n" attribute which contains the friendly name:
``` javascript
{"ctl":{"ret":"ok","tp":"sa","msid":"11","m":[{"mid":"0","n":"Entry"},{"mid":"1","n":"Master Bath"},{"mid":"2","n":"Master"},{"mid":"3","n":"Office"},{"mid":"4","n":"Play Room"},{"mid":"5","n":"Craft Room"},{"mid":"6","n":"Kitchen"},{"mid":"7","n":"Sun Room"},{"mid":"8","n":"Garage Entry"}]}}
```
Remove the api response details ("ctl" and "ret"):
``` javascript
{"tp":"sa","msid":"11","m":[{"mid":"0","n":"Entry"},{"mid":"1","n":"Master Bath"},{"mid":"2","n":"Master"},{"mid":"3","n":"Office"},{"mid":"4","n":"Play Room"},{"mid":"5","n":"Craft Room"},{"mid":"6","n":"Kitchen"},{"mid":"7","n":"Sun Room"},{"mid":"8","n":"Garage Entry"}]}
```
Lastly use the below command to issue the rename:
```
vacbot.run(VacBotCommand("RenameM", {"tp":"sa","msid":"11","m":[{"mid":"0","n":"Entry"},{"mid":"1","n":"Master Bath"},{"mid":"2","n":"Master"},{"mid":"3","n":"Office"},{"mid":"4","n":"Play Room"},{"mid":"5","n":"Craft Room"},{"mid":"6","n":"Kitchen"},{"mid":"7","n":"Sun Room"},{"mid":"8","n":"Garage Entry"}]}))
```
You should then see the friendly names in the app when selecting an area to clean.

**Note:** You cannot use the friendly names when starting a clean, you must use the mid.

