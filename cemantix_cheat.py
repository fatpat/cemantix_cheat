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
import sys
import getopt
import json
import atexit

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

#    # test argv for pre words
#    if len(sys.argv) > 1:
#        print("len(sysargv)=%d" % len(sys.argv))
#        for word in sys.argv[1:]:
#            print("arg -> %s" % word)
#            if word not in tested_words:
#                print("arg selected -> %s" % word)
#                return word
    
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

def usage():
    print("%s: [-h|--help] [-c|--cache /path/to/cache_file] [-o|--operation|--op search|start]" % sys.argv[0])

#
# MAIN CODE
#
BASE_URL = "https://cemantix.herokuapp.com"
MODEL = "frWac_postag_no_phrase_700_skip_cut50.bin"
CACHE_FILE = None
OPERATION = None

# a map[string]score to follow which words have been already tested
tested_words = {}

# a map[percentil]array[word] to follow closed words
closed_words = []

# an array[string] to register word already known as unknown
unknown_words = []

def save_cache_file(f):
    if f:
        print("saving unknown words to cache file %s" % f)
        with open(f, 'w') as fd:
            json.dump(unknown_words, fd)

try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:o:", ["help", "cache=", "operation=", "op="])
except getopt.GetoptError as e:
    print("Error: ", e)
    usage()
    sys.exit(2)

for opt, arg in opts:
    if opt in ("-h", "--help"):
        usage()
        sys.exit()

    if opt in ["-c", "--cache"]:
        CACHE_FILE=arg
        continue

    if opt in ["-o", "--op", "--operation"]:
        OPERATION=arg
        continue

if OPERATION not in ("search", "start"):
    print("operation must be 'search' or 'start'")
    usage()
    sys.exit(1)

if CACHE_FILE:
    try:
        with open(CACHE_FILE) as fd:
            unknown_words = json.load(fd)
            if type(unknown_words) is not list:
                raise("Cache file %s must be an array", CACHE_FILE)
            for w in unknown_words:
                if type(w) is not str:
                    raise("Cache file %s must be an array of strings only", CACHE_FILE)
    except Exception as e:
        print("error while reading %s, skipping: %s" % (CACHE_FILE, e))

    atexit.register(save_cache_file, CACHE_FILE)


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

    if word in unknown_words:
        print("%s -> skipping because it's an unknown word (from cache)", word)
        tested_words[word] = -1 # record the words to prevent from extracting it again in choose_next_word()
        continue

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
        unknown_words.append(word)
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
        if OPERATION == "start":
            sys.exit(0)
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
