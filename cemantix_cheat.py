#!/usr/bin/env python3

import time
import requests
from datetime import datetime, timedelta
import humanize
from gensim.models import KeyedVectors
from collections import Counter
import itertools
import pprint
import random
import re

#
# test a word against the game
#
def test_word(word):
    body = {'word' : word}
    r = requests.post("%s/score" % BASE_URL, data=body, timeout=0.5)

    # prevent overkilling the game by sleeping between 250ms and 2s
    time.sleep(random.randrange(250,2000)/1000)

    if r.status_code != 200:
        raise Exception("/score returned %d" % r.status_code)

    if r.headers['Content-Type'] != 'application/json':
        raise Exception("/score returned wrong Content-Type (%s)" % r.headers['Content-Type'])

    return r.json()

#
# choose the next word
#
def choose_next_word():

    # ensure all the words have not yet been tested
    if len(tested_words) == number_of_words:
        raise Exception("All words have been tried ... no luck")

    # try from closed_words
    # iterate through the already tested words that were close
    # from the closest word with the highest score (which is 1000)
    for i in range(1000,-1,-1):

        # loop over each word for this score
        for word in closed_words[i]:

            # find 10 similarities and loop over
            for i in model.most_similar(word, topn=10):

                # extract the word
                word = i[0]

                # return if not already tested
                if word not in tested_words:
                    return word
    
    # if all words from similarities have already been tested
    # failover to random words from the model
    while len(tested_words) != number_of_words:
        word = random.choice(model.index_to_key)

        # ensure the word has not been tested already
        if word not in tested_words:
            return word

        print("word '%s' already tested, choosing a new one" % word)
        return choose_next_word()

    raise Exception("All words have been tried ... no luck")

#
# MAIN CODE
#
BASE_URL = "https://cemantix.herokuapp.com"
MODEL = "frWac_postag_no_phrase_700_skip_cut50.bin"

# a map[string]score to follow which words have been already tested
tested_words = {}

# a map[percentil]array[word] to follow closed words
closed_words = []

# init closed_words array
# percentil can go up to 1000
for i in range(0,1000+1):
    closed_words.append([])

# load the model
model = KeyedVectors.load_word2vec_format(MODEL, binary=True, unicode_errors="ignore")

# number of words in the model
number_of_words = len(model.index_to_key)

# number of tries not in error
tries = 0

time_start = datetime.now()
word = ""
while True:
    # choose the next word
    word = choose_next_word()

    # test the word (and remove the suffix (_n, _v, _adv, ...)
    try:
        s = test_word(re.sub('_\w+$', '', word))
    except Exception as e:
        print("%s -> error (%s)" % (word, e))
        tested_words[word] = -1
        continue

    # record the tested word to prevent testing it again
    tested_words[word] = -1

    # word in error
    if 'error' in s:
        print("%s -> unknown" % word)
        continue

    tries = tries + 1

    # word found !
    if s['score'] >= 1:
        break
    
    # store the score in case (not used for now)
    tested_words[word] = s['score']

    # closed word 
    # when percentile is returned, this means the word is closed to the solution
    if 'percentile' in s:

        # backup the word
        if closed_words[s['percentile']] is None:
            closed_words[s['percentile']] = []
        closed_words[s['percentile']].append(word)

        print("%s -> close %d" % (word, s['percentile']))
        continue


    print("%s -> %f" % (word, s['score'] * 100))

#
# End, stats and stuff
#
time_stop = datetime.now()
duration = time_stop - time_start

print("")
print("Word of the day found: %s ! congratulations" % re.sub('_\w+$', '', word))
print("")
print("Statistics:")
print("  number of tries : %d" % tries)
print("  number of errors: %d" % len(tested_words))
print("  duration        : %s" % humanize.precisedelta(duration))
print("")
