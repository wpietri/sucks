sucks
=====

A simple command-line python script to drive a robot vacuum. Currently
works only with the Ecovacs Deebot N79, as that's what I have.

This only covers my simple use case. There's a lot more it could do.
If you'd like to help flesh it out, send email to my first name at
williampietri.com.

If you're curious about the protocol, I have [a rough
doc](protocol.md) started. I'll happily accept pull requests for it.

Why the project name? Well, a) it's ridiculous that I needed to MITM
my own vacuum.  This is not the future I signed up for. There should
be a nice, tidy RESTful API. That would be easy enough to make. And b),
it's a vacuum.

## Usage

To get started, you'll need to have already set up an EcoVacs account
using your smartphone. I've only tested this with Android, but I expect
it will work with iPhone-created accounts as well.

Step one is to log in:
```
    % sucks login
    Ecovacs app email: [your email]
    Ecovacs app password: [your password]
    Config saved.
```

That creates a config file in ~/.config.sucks.conf. The password is
hashed before saving, so it's reasonably safe.

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


## Thanks

My heartfelt thanks to:

* [xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html),
a great library for examining XMPP traffic flows. (Yes, your vacuum
speaks Jabbber!)
* [mitmproxy](https://mitmproxy.org/), a fantastic tool for analyzing HTTPS.
* [click](http://click.pocoo.org/), a wonderfully complete and thoughtful
library for making Python command-line interfaces
* [requests](http://docs.python-requests.org/en/master/), a polished Python
library for HTTP requests, and
* Albert Louw, who was kind enough to post code from
[his own experiments](https://community.smartthings.com/t/ecovacs-deebot-n79/93410/33)
with his device.





## To Do

* add a status commmand
