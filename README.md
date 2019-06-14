Linux: [![Build Status](https://travis-ci.org/wpietri/sucks.svg?branch=master)](https://travis-ci.org/wpietri/sucks)
Windows: [![Build Status](https://ci.appveyor.com/api/projects/status/github/wpietri/sucks)](https://ci.appveyor.com/project/wpietri/sucks)


sucks
=====

A simple command-line python script to drive a robot vacuum. Currently
known to work with the Ecovacs Deebot N79, M80 Pro, M81, M88
Pro, and R95 MKII from both North America and Europe.

Does it work for your model as well? Join the discussion on the
[sucks-users mailing
list](https://groups.google.com/forum/#!forum/sucks-users).

If you're curious about the protocol, I have [a rough doc](http://github.com/wpietri/sucks/blob/master/protocol.md)
started. I'll happily accept pull requests for it.

Why the project name? Well, a) it's ridiculous that I needed to MITM
my own vacuum.  This is not the future I signed up for. And b),
it's a vacuum.

## Installation

If you have a recent version of Python 3, you should be able to
do `pip install sucks` to get the most recently released version of
this.

## Usage

To get started, you'll need to have already set up an EcoVacs account
using your smartphone.

With that ready, step one is to log in:
```
    % sucks login
    Ecovacs app email: [your email]
    Ecovacs app password: [your password]
    your two-letter country code: us
    your two-letter continent code: na
    Config saved.
```

That creates a config file in a platform-appropriate place. The password
is hashed before saving, so it's reasonably safe. (If it doesn't appear
to work for your continent, try "ww", their world-wide catchall.)

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

If you wanted it to clean for 5 minutes and then stop without charging:

```
    % sucks clean 5 stop
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
so it also has a mode where it randomly decides to run or not based on
a frequency you give it. My crontab entry looks like this:

```
0 10 * * * /home/william/projects/sucks/sucks.sh clean -f 4/7 15 edge -f 1/14 10
```

This means that every day at 10 am, it might do something. 4 days out
of 7, it will do 15 minutes of automatic cleaning. 1 day out of 14,
it will do 10 minutes of edging. And afterward it will always go back to
charge.

## Library use

You are welcome to try using this as a python library for other efforts. The
API is still experimental, so expect changes. Please join the [mailing
list](https://groups.google.com/forum/#!forum/sucks-users) to participate in
shaping the API.

A simple usage might go something like this:

```python
from sucks import *

config = ...

api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'],
                         config['country'], config['continent'])
my_vac = api.devices()[0]
vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, my_vac, config['continent'])
vacbot.connect_and_wait_until_ready()

vacbot.run(Clean())  # start cleaning
time.sleep(900)      # clean for 15 minutes
vacbot.run(Charge()) # return to the charger
```

## Developing

If you'd like to join in on developing, I recommend checking out the code,
setting up a virtual environment, and installing this package in editable
mode. You can confirm your environment works by running the tests. And please
do join the [mailing list](https://groups.google.com/forum/#!forum/sucks-users)
to discuss your plans.

For more information see [the development documentation](developing.md).



## See also

There are now similar libraries in [Javascript](https://github.com/joostth/sucks.js)
and [Go](https://github.com/skburgart/go-vacbot).

## Thanks

My heartfelt thanks to:

* [xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html),
a great library for examining XMPP traffic flows (yes, your vacuum
speaks Jabbber!),
* [mitmproxy](https://mitmproxy.org/), a fantastic tool for analyzing HTTPS,
* [click](http://click.pocoo.org/), a wonderfully complete and thoughtful
library for making Python command-line interfaces,
* [requests](http://docs.python-requests.org/en/master/), a polished Python
library for HTTP requests,
* [Decompilers online](http://www.javadecompilers.com/apk), which was
very helpful in figuring out what the Android app was up to,
* Albert Louw, who was kind enough to post code from [his own
experiments](https://community.smartthings.com/t/ecovacs-deebot-n79/93410/33)
with his device, and
* All the users who have given useful feedback and contributed code!
