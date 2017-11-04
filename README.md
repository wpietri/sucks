sucks
=====

A simple command-line python script to drive a robot vacuum. Currently
works only with the Ecovacs Deebot N79, as that's what I have.

Right now this code offered more as inspiration than something for other
people to just download and use. But if you'd like to help flesh it out,
send email to my first name at williampietri.com.

If you're curious about the protocol, I have [a very rough
doc](protocol.md) started. I'll happily accept pull requests for it.

Why the project name? Well, a) it's ridiculous that I needed to MITM
my own vacuum.  This is not the future I signed up for. There should
be a nice, tidy RESTful API. That would be easy enough to make. And b),
it's a vacuum.

## Usage

If you do try to use it, you'll need to create ~/.config/sucks.conf. It
should look something like this:

```
user=20170101abcdef0123456
domain=ecouser.net
resource=abcdef01
secret=[long base64 string]
vacuum=[robot id]@126.ecorobot.net
```

I got these values by using
[xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html) to do
a man-in-the-middle attack on the android app. You can use the included
log_clean.py script to generate a config from a captured session. (I
suspect that the Android app re-keys the connection on a regular basis,
as the secret was changing regularly up until I cleared the Android
app's data from my phone.) Tip: tell your router to lie to your phone
about the hostname msg-na.ecouser.net. I pointed that to the laptop
where I was running xmpppeek and things went smoothly.

With that set up, you could have it clean in auto mode for 10 minutes
and return to its charger:

```
    % sucks clean 10
```

You could have it clean for 15 minutes and then do an extra 10 minutes
of edging:

```
    % sucks clean 15 edge 10
```

If you wanted it to clean for 5 minutes and then stop where it was,
either of these would work:

```
    % sucks clean 5 stop
    % sucks --no-charge clean 5
```

If it's running amok and you'd just like it to stop where it is:

```
    % sucks stop
```

To tell it to go plug in:

```
    % sucks charge
```

I run mine from my crontab, but I didn't want it to clean every day,
so it also has a mode where it randomly decide to run or not based on
a frequency you give it. My crontab entry looks like this:

```
0 10 * * * /home/william/projects/sucks/sucks clean -f 4/7 15 edge -f 1/14 10
```

This means that every day at 10 am, it might do something. 4 days out
of 7, it will do 15 minutes of automatic cleaning. 1 day out of 14,
it will do another 10 minutes of edging. And afterward it will always
go back to charge.


## To Do

* add a status commmand
