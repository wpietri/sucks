sucks
=====

A simple command-line python script to drive a robot vacuum. Currently
works only with the Ecovacs Deebot N79, as that's what I have.

Right now this code offered more as inspiration than something for other
people to just download and use. But if you'd like to help flesh it out,
send email to my first name at williampietri.com.

If you do try to use it, you'll need to create ~/.config/sucks.conf. It
should look something like this:

```
email=user@example.org
user=2017010101abdef012345
domain=ecouser.net
resource=abcdef01
secret=[long base64 string]
vacuum=[robot id]@126.ecorobot.net
```

I got these values by using xmppeek to do a man-in-the-middle attack on
the android app. I suspect that the Android app re-keys the connection
on a regular basis, as the secret was changing regularly up until I
cleared the Android app's data from my phone. It should be possible to
give this tool a command something like "login" that would create the config
file automatically.

## To Do

* implement common commands
* stop sending back error messages in response to robot updates
* track robot state (e.g., cleaning, stopped)
* use tracked state to be smarter
* log activity to aid in debugging
* add probabilistic cleaning options
