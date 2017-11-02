
A clean command:
```
<iq id="TXID" to="ROBOTID@126.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl"><ctl td="Clean"><clean type="auto" speed="standard"/></ctl></query></iq>

```

A charge command:
```
<iq id="TXID" to="ROBOTID@126.ecorobot.net/atom" from="USERID@ecouser.net/RESOURCEID" type="set"><query xmlns="com:ctl"><ctl td="Charge"><charge type="go"/></ctl></query></iq>
```