# Developer Attacks Robot! (adventures in reverse engineering)

## outline

- Introduction -
    - I'm writing this up because these skills aren't just useful for dealing with robots; they're a good way to figure out existing systems debugging legacy code.
    - I'm doing this all with Linux, but this all can be done
- snoop the traffic - let's set up as an access point and just use Wireshark to see what it's doing.
    - close everything, put it in battery-saving mode
    - DNS! Fine!
    - HTTPS! Urgh.
    - And what's this stuff?
- XMPP
    - what's this protocol
    - it's controlling the vacuum, so let's dig in
    - what can I use? aha, mitmproxy
    - wow, that's a bunch of junk!
    - boil it down some
    - boil it down some more
- start hacking
    - simple XMPP script
    - what's this auth stuff
    - an RFC side trip
    - send some commands
    - oh my god, it works!
- auth troubles
    - now it doesn't work, what happened?
    - the android app is breaking things
    - now we have to look at the HTTPS stuff
    - mitmproxy to the rescue
- HTTPS
    - 6 calls in 2 sets but hey, there in #4 is a token that works
    - Let's make our hack script work for the second set
    - it works! But what about this garbage?
    - We can't figure it out from the protocol alone. To the code!
- APK decompliation
    - Let's search for key strings
    - Well, that's some strings. Where are the rest?
    - Ok, more strings. Let's try implementing something.
    - Can we send it with no signature? Nope.
    - Can we send it with a fake signature? Nope.
    - Gotta do it for real. Let's bring it!
    - Hack, fail, hack, fail. (Scary! Low feedback!) Hack, succeed!
- Wrapping up
    - Let's make a tidy final script (and share it!)
    - What did we learn?

## tl;dr

I bought a robot vacuum. The control app didn't do quite what I wanted. Here I
explain in too much detail how I figured out how the app was talking to the robot
so that I could control it from my own code. Tools used include Wireshark,
mitmproxy, xmppproxy, adb, and a Java decompiler.

## introduction

After many years as a sysadmin and developer, after thousands of hours spent
running down problems, this is basically how I feel about other people's code:

> I don't know who you are. I don't know what you want. If you are looking for
> ransom I can tell you I don't have money, but what I do have are a very
> particular set of skills. Skills I have acquired over a very long career.
> Skills that make me a nightmare for people like you.
> -- [Liam Neeson, Taken](http://www.esquire.com/entertainment/movies/a31775/taken-speech/)

<!-- TODO: insert Taken photo -->

Recently, I bought a robot vacuum, the [Wirecutter-recommended](https://thewirecutter.com/reviews/best-robot-vacuum/)
[EcoVacs Deebot N79](https://www.ecovacs.com/us/deebot-robotic-vacuum-cleaner/DEEBOT-N79/).
It's honestly a pretty swell piece of hardware. Watching it go, it's clear that
it's the product not just of smarts, but of a lot of thoughtful experimentation.
Compared with the early Roomba I had, it feels *evolved*.

But the Android app is... not as good. In particular, you can have it start
cleaning at a certain time. However, it only stops cleaning when it runs out
of battery, or circa 90 minutes. My place is small; I need maybe 10 minutes
of daily cleaning. That bothered me. It's a mechanical device, and its brushes
and filters are consumables. It's not expensive, but having it waste 8/9ths
of its lifespan cleaning already-clean floors bugged me. I also didn't need
the extra noise and hassle.

So first, to Google! Did anybody already fix this? Nope. Is there a public API?
Nope. Have other people looked into this? Turns out yes! There was a forum
post with a little discussion and some sample code. Which was interesting,
but not enough to build from. How to I find out how to control my property?

Here follows my answer to that. It's a cleaned-up version of my explorations,
written to share some of my tricks with others, and help people get more
comfortable figuring out what the hell is going on with their tech. My
target audience is people who code at least enough to be dangerous. By the
end, I hope you'll be more dangerous.


## you say you wanna snoop

The first quesiton to answer: what the hell is that app doing?: Modern phones are,
for good reason, basically sealed boxes. I could root my phone so that I could do
more effective debugging from there. But since I mainly care about what it's doing
over the network, I'm going to start with snooping the network traffic.

### Wireshark to the rescue!

An easy way to capture all that traffic is to make your laptop a wifi router.
I"m using an Ubuntu laptop, so I needed to plug into an Ethernet network and then
make a few [simple networking changes](https://askubuntu.com/questions/180733/how-to-setup-an-access-point-mode-wi-fi-hotspot).
(Other OSes have similar functionality, so you should be able to play along.)
Once I got that working, I connected my phone to the new wifi access point.

The next step was to make things clean and simple. Complexity is the enemy of
any good debugging effort. I put my phone in Battery Saver mode, which
minimizes background activity. I force-stopped the EcoVacs app and cleared
out its data, so we were starting fresh. Then I rebooted my phone, turned
Battery Saver back on, and let it sit for a couple minutes so its startup
activity was hopefully complete.

<!--TODO: Screnshots of battery saver, etc-->

I also checked out the network settings to see what my phone's
IP was. That will become important once we have some packets captured.

That ready, I started up one of my favorite tools, Wireshark. This is basicially
x-ray vision for networks, and it is fucking magic. It has a zillion options
and tools and protocol decoders, most of which we will studiously ignore. I
told it to start capturing my wireless interface. It shows you what's happening
in real time, so I saw various traffic ticking by, including a bunch of Google
stuff. That seemed good, and it was my phone's IP address, so I was capturing
the right activity.

Now to start up the app! I jotted down the exact time in my notes and started
up the EcoVacs app. I noted the time I hit the login button, and watched it
churn for a bit as it found my vacuum and got connected. I noted the time again
when I told the vaccum to start cleaning. After a bit, I told it to go back to
its charger. When all was quiet again, I stopped the capture.

[SIDEBAR: In this article, I'm making it sound like I did things once. The
truth is that I did most of these steps many times, separated by periods of
confusion and swearing. You're getting the edited version here, because the
truth would be deadly dull. But as you go through this, don't be discouraged
if you have to try something again and again because the results were messy
or puzzling.]

### what's all this garbage?

If you're playing along, you now have a screen with a lot of technical-looking
stuff, done up in the [angry fruit salad](http://catb.org/jargon/html/A/angry-fruit-salad.html)
school of user interface design. Scrolling, there are thousands of entries,
each more arcane than the last. What is it?

Well, honestly, for the moment I don't care , and you shouldn't either. There's 30 years of
layered technical history that is undeniably cool and interesting. Your
phone does a lot! Other things on your network are also doing a lot! Later
on you can come back, pick a random packet, and try to figure out what it's
doing. But for now, you should treat this like you're an easily distractable
person shopping at a megastore. Don't look at everything; just find what you
need and get the hell out.

A great place to start is DNS. That is the protocol where domain names get
turned into internet addresses, a necessary step before any connection is made
Since DNS mostly runs over UDP port 53, I type in a filter at the top of the
window: "udp.port==53". (How did I know it was 53? Experience. But you can
check out a [short list](http://www.pearsonitcertification.com/articles/article.aspx?p=1868080)
of common port numbers or Wikipedia's [more comprehensive list](https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers).)
Now I have a fair bit less garbage. I see queries
about things I know are on my phone: Wikipedia, Lastpass, Mint, and of course
Google.

As I get down to the timestamp for when I started the app, I see a familiar
name: ecovacs.com. <!-- TODO: insert screnshot 500 -->
That's a good sign! Now I'm in the right place. I set the this a a timestamp
reference. <!-- TODO: insert screnshot 502 --> Now the times are relative
to when the app got going, making it easier for me to keep track of things.
<!-- TODO: insert screnshot 503 --> Scrolling down, I see it look up some
related domain names: eco-us-api.ecovacs.com, users-na.ecouser.net,
ne-na.ecouser.net, msg-na.ecouser.net, and a few others. I keep those in
mind for future investigation.

Now that I'm in the right ballpark, I clear the filter and start looking
at the raw traffic. What does it do right after it looks up the eco-us-api
name? It connects to it! Yay! There are a whole bunch of packets going back
and forth between my phone and that server. If I clieck on the first, Wireshark
even shows in the left edge that all those packets are related. <!-- TODO: insert screnshot 505 -->

However, the fact that it's connecting to port 443 is a problem. That's the
port for HTTPS. The S meaning Secure, meaning encrypted, meaning naughty
snoopers like us can't see anything useful. There's a solution for that, but
let's keep looking and see what else we have.

Further down, there's a connection on port 5223. <!-- TODO: insert screnshot 508 -->
That's unusual, and Wireshark
just calls the protocol TCP, meaning it's not sure what to make of it. What
is it? To find out, I bring up the menu for one of the packets, pick "Follow",
and then "TCP Stream". This pulls all the packets together for connection,
extracts the payload as texts, and then displays the client as red and the
server as blue.

<!-- TODO: insert screnshot 509 -->

This is one of my favorite Wireshark tools. Expecially for plain HTTP and other
non-encrypted protocols, it's great for seeing what's really going on. Here,
we see some XML at the top and then it decends into mostly garbage. Let's look
at the XML.

<!-- TODO: format and colorize -->

```
<stream:stream to="ecouser.net" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams" version="1.0">

<stream:stream xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client" version="1.0" id="a85619c3ea44f395f651faf1a5996ee6" from="ecouser.net">

<stream:features>
    <auth xmlns="http://jabber.org/features/iq-auth"/>
    <starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls">
        <required/>
    </starttls>
    <mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl">
        <mechanism>PLAIN</mechanism>
    </mechanisms>
</stream:features>

<starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"/>

<proceed xmlns="urn:ietf:params:xml:ns:xmpp-tls"/>
```

I don't know much about this, but there's an obvious hint. So I look at
jabber.org, and it mentions XMPP. I hazily recall Jabber as an instant
messaging tool, and XMPP is the protocol. That seems weird, but the
[XMPP website](https://xmpp.org/) mentions that a common use case is
Internet of Things. That makes some sense. If you have a lot of things,
like my phone, wanting to talk occasionally to other things, like my robot vacuum,
IM is a well-tested approach.

The TLS thing, though, is a bit of a problem. When it says starttls, it's
upgrading from the insecure connection, which we can read, to a secure
connection, which we can't. (For more, see Wikipedia's [Opportunistic TLS](https://en.wikipedia.org/wiki/Opportunistic_TLS)
article.) But there's some good news. As I scroll down in the Wireshark
extract, I see this bit:

```
AU1.0...U...
Some-State1!0...U.
..Internet Widgits Pty Ltd
```

AU? Some State? Interenet Widgits? I recognize those as default values
for a [self-signed certificate](https://en.wikipedia.org/wiki/Self-signed_certificate).
That means the app is maybe not so serious about security here. So this seems
like a good place to break in.

## robot jabber

I do a little more reading on [XMPP](https://en.wikipedia.org/wiki/XMPP).
It's a proper internet standard and everything, so I flip through [RFC 6120](https://tools.ietf.org/html/rfc6120),
[RFC 6121](https://tools.ietf.org/html/rfc6121), and [RFC 6122](https://tools.ietf.org/html/rfc6122),
the standards documents that describe it. It feels like (and is) something
from the late 90s, when XML was all the rage.

I rummage around a bit, an a search for "xmpp mitm" (that being Man In The Middle),
I find [xmpppeek](https://www.beneaththewaves.net/Software/XMPPPeek.html), an
XMPP proxy. I love this kind of thing: somebody made it for their own needs,
found it useful, and put it up on the Internet just in case.

### looking inside the XMPP

I install xmpppeek. But how to get the app to talk to my server instead of
the real one? Lies. In particular, my router lets me set up hostnames. That's
probably so I can easily set up a home server, but here, I'll abuse it. I tell
it to lie about the address for [TODO: server name] and return my laptop address
instead. Then I start up xmpppeek and tell it to forward to the real EcoVacs
server. It complains, saying it needs its own encryption certificate. I can
never remember the incantation for that, but the Internet does, so shortly it's
up and running. Will it work?

I start up the Ecovacs app and shit starts scrolling on my laptop screen:

<!-- Insert screenshot 510 -->

I don't know what half of this means, but we can definitely see farther than
before into the XMPP transaction, so this looks like a step forward. And this
bit is particularly interesting:

```
[2017-11-15 14:49:48.016593-0MjAxNzEwMjU1OWYwZWU2M2M1ODhkADIwMTcxMDI1NTlmMGVlNjNjNTg4ZAAwLzEzYjQxMjk5L2V5aDlXZ0NOOVFkWGxEZkNDY1I1cVBBMUtLSnZ4eWts7:00] [(S2C) 47.88.66.164:5223 -> 192.168.1.227:48607] }}}<stream:features><auth xmlns="http://jabber.org/features/iq-auth"/><mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl"><mechanism>PLAIN</mechanism></mechanisms></stream:features>{{{
[2017-11-15 14:49:48.255088-07:00] [(C2S) 192.168.1.227:48607 -> 47.88.66.164:5223] }}}<auth mechanism="PLAIN" xmlns="urn:ietf:params:xml:ns:xmpp-sasl">MjAxNzEwMjU1OWYwZWU2M2M1ODhkADIwMTcxMDI1NTlmMGVlNjNjNTg4ZAAwL2VmY2Y5M2U2L2dyOWhDZkc0Q3NmeVU3QlRQeVRDNkJaWVgxQjFVazhE</auth>{{{
[2017-11-15 14:49:48.444622-07:00] [(S2C) 47.88.66.164:5223 -> 192.168.1.227:48607] }}}<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>{{{
```

The server says, "for authenticating, I like the PLAIN method". The client says,
"cool, here's a lump of PLAIN auth". The server says, "success". And then we say,
in our best hacker voices, "I'm in!" If we can authenticate with something
straightforward, maybe we're good to go.

Fishing further, I see something that looks like a username "2017102559f0ee63c588d@ecouser.net". Maybe that will come
in handy.There are also
nice bits of XML like `<ctl td="Clean"><clean type="auto" speed="standard"/></ctl>`
when I hit the auto-clean button in the app, and `<ctl td="Clean"><clean type="stop" speed="standard"/></ctl>`
when I have it stop. Once we're connected, bossing the robot around should be easy.
So how do we get connected?

## ruby slippers

For things like this, I like Ruby and Python. The languages are easy to get
started with, forgiving, and they have a ton of libraries. For this, let's try
Ruby. I quickly find an [XMPP client library](http://xmpp4r.github.io/) that
isn't too stale and even a
[simple how-to article](https://www.sitepoint.com/looking-xmpp-xmpp4r-gem/).
So let's see if we can build something that at least talks to the server.

I use bundler to install the xmpp4r gem and then write the dumbest possible
program:

```
require 'xmpp4r'
require 'xmpp4r/client'

include Jabber


Jabber.debug = true

jid = JID.new('2017102559f0ee63c588d@ecouser.net')
client = Client.new(jid)
client.connect
```

I run that and it works! It connects. It doesn't do anything, but I'm on
the right trail. Can we log in just using the magic string from the XML
above? I add this:

```
client.auth('MjAxNzEwMjU1OWYwZWU2M2M1ODhkADIwMTcxMDI1NTlmMGVlNjNjNTg4ZAAwL2VmY2Y5M2U2L2dyOWhDZkc0Q3NmeVU3QlRQeVRDNkJaWVgxQjFVazhE')

```

Does it work? No. In the debugging output, it sends a different, longer
string than the one we gave it. Now, alas, we have to actually learn
something about how this works. Luckily, XML is an implausibly verbose
protocol, and looking at the auth exchange there are valuable clues like
SASL and PLAIN. Going back to the [XMPP spec](https://tools.ietf.org/html/rfc6120#section-6)
there is a whole section on SASL, and SASL even has an [RFC of its own](https://tools.ietf.org/html/rfc4422).
The XMPP RFC tells us that data gets encoded as base64. So let's try
decoding that.

```
$ base64 -d
MjAxNzEwMjU1OWYwZWU2M2M1ODhkADIwMTcxMDI1NTlmMGVlNjNjNTg4ZAAwL2VmY2Y5M2U2L2dyOWhDZkc0Q3NmeVU3QlRQeVRDNkJaWVgxQjFVazhE
2017102559f0ee63c588d2017102559f0ee63c588d0/efcf93e6/gr9hCfG4CsfyU7BTPyTC6BZYX1B1Uk8D
```
I give it the first line; it gives me the second. The first part of that
looks like the username above, but then it trails off into nonsense.
What's the rest? More rummaging leads me to [RFC 4616](https://tools.ietf.org/html/rfc4616),
which is specifically about SASL PLAIN. There it explains the format:

```
   message   = [authzid] UTF8NUL authcid UTF8NUL passwd
   authcid   = 1*SAFE ; MUST accept up to 255 octets
   authzid   = 1*SAFE ; MUST accept up to 255 octets
   passwd    = 1*SAFE ; MUST accept up to 255 octets
   UTF8NUL   = %x00 ; UTF-8 encoded NUL character
```

That's somewhat helpful. A password is somethign I understand. The docs say
that the two ids are the *authentication id* and the *authorization id*. I
don't know what the difference is, but I have learned that there is probably
a NUL character, which doesn't show up on my screen.

To see it, I whip out one of my favorite tools: od. This is an old-school
Unix utility, short for "octal dump", because octal numbers were used heavily
back in the day. (Now generally we use hex.) But it does a ton more than that.
In particular, its `-c` option will dump things as characters when it can, and
then show us the hidden things. So now I try again:

```
$ base64 -d | od -c
MjAxNzEwMjU1OWYwZWU2M2M1ODhkADIwMTcxMDI1NTlmMGVlNjNjNTg4ZAAwL2VmY2Y5M2U2L2dyOWhDZkc0Q3NmeVU3QlRQeVRDNkJaWVgxQjFVazhE
0000000   2   0   1   7   1   0   2   5   5   9   f   0   e   e   6   3
0000020   c   5   8   8   d  \0   2   0   1   7   1   0   2   5   5   9
0000040   f   0   e   e   6   3   c   5   8   8   d  \0   0   /   e   f
0000060   c   f   9   3   e   6   /   g   r   9   h   C   f   G   4   C
0000100   s   f   y   U   7   B   T   P   y   T   C   6   B   Z   Y   X
0000120   1   B   1   U   k   8   D
0000127
```

This is much better. The NUL character shows up as \0 here. So we can see
that the `authcid` is our username. And the `authzid` is too, so I guess we
don't have to understand the difference. And the rest must be the password.
Let's try authenticating with that.

And no! It doesn't work. But why? Looking at the debugging output from the
script, I try feeding that into od -c as well. And I discover that it is
sending the @ecouser.net as part of the username. That's no good! Maybe
the username's just the first part.


SOMETHING ELSE IS FUCKED UP ABOUT THIS LIBRARY. I taught it to do EcoVacs
style auth and it is definitely not working. So there's something else in the
flow that isn't right. But what?
