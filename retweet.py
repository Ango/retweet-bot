#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ConfigParser
import tweepy
import inspect
import hashlib

path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

# read config
config = ConfigParser.SafeConfigParser()
config.read(os.path.join(path, "config"))

# your hashtag or search query and tweet language (empty = all languages)
hashtag = config.get("settings", "search_query")
tweet_language = config.get("settings", "tweet_language")
comment = config.get("settings", "comment")
retweets_limit = int(config.get("settings", "retweets_limit"))

# blacklisted users and words
user_blacklist = []
word_blacklist = ["RT", u"♺"]

# build savepoint path + file
hashed_hashtag = hashlib.md5(hashtag).hexdigest()
last_id_filename = "last_id_hashtag_{}".format(hashed_hashtag)
rt_bot_path = os.path.dirname(os.path.abspath(__file__))
last_id_file = os.path.join(rt_bot_path, last_id_filename)

# create bot
auth = tweepy.OAuthHandler(config.get("twitter", "consumer_key"), config.get("twitter", "consumer_secret"))
auth.set_access_token(config.get("twitter", "access_token"), config.get("twitter", "access_token_secret"))
api = tweepy.API(auth)

# retrieve last savepoint if available
try:
    with open(last_id_file, "r") as f:
        savepoint = f.read()
except IOError:
    savepoint = ""
    print "No savepoint found. Trying to get as many results as possible."

# search query
timeline_iterator = tweepy.Cursor(api.search,
                                  q=hashtag,
                                  since_id=savepoint,
                                  lang=tweet_language).items(retweets_limit*2)

# put everything into a list to be able to sort/filter
timeline = []
for status in timeline_iterator:
    timeline.append(status)

try:
    last_tweet_id = timeline[0].id
except IndexError:
    last_tweet_id = savepoint

# filter @replies/blacklisted words & users out and reverse timeline
timeline = filter(lambda status: status.text[0] != "@", timeline)
timeline = filter(lambda status: not any(word in status.text.split() for word in word_blacklist), timeline)
timeline = filter(lambda status: status.author.screen_name not in user_blacklist, timeline)
# slice due to limit
timeline = timeline[:retweets_limit]
timeline.reverse()

tw_counter = 0
err_counter = 0

# iterate the timeline and retweet
for status in timeline:
    try:
        print "({date}) {name}: {message}\n".format(date=status.created_at,
                                                    name=status.author.screen_name.encode('utf-8'),
                                                    message=status.text.encode('utf-8'))

        if comment:
            tweet_url = "https://twitter.com/{user_id}/status/{tweet_id}".format(user_id=status.author.id,
                                                                                 tweet_id=status.id)
            status_message = "{comment} {tweet_url}".format(comment=comment, tweet_url=tweet_url)
            api.update_status(status=status_message, in_reply_to_status_id=status.id)
        else:
            api.retweet(status.id)

        tw_counter += 1
    except tweepy.error.TweepError as e:
        # just in case tweet got deleted in the meantime or already retweeted
        err_counter += 1
        #print e
        continue

print "Finished. %d Tweets retweeted, %d errors occured." % (tw_counter, err_counter)

# write last retweeted tweet id to file
with open(last_id_file, "w") as file:
    file.write(str(last_tweet_id))

