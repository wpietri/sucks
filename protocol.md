The core protocol is XMPP. The Android app establishes a connection to an XMPP server and logs in using
a secret that the android app appears to change from time to time. It then sends XMPP IQ commands. It describes
them as queries, but they all contain "ctl" elements that appear to be commands. Here are a couple of full
examples with the private information removed:


A clean command:
```
<iq id="TXID" to="ROBOTID@126.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl"><ctl td="Clean"><clean type="auto" speed="standard"/></ctl></query></iq>

```

A charge command:
```
<iq id="TXID" to="ROBOTID@126.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl"><ctl td="Charge"><charge type="go"/></ctl></query></iq>
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
