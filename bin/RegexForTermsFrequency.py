#!/usr/bin/env python2
# -*-coding:UTF-8 -*
"""
This Module is used for term frequency.

"""
import redis
import time
from pubsublogger import publisher
from packages import lib_words
from packages import Paste
import os
import datetime
import calendar
import re

from Helper import Process

# Config Variables
DICO_REFRESH_TIME = 60 #s

BlackListTermsSet_Name = "BlackListSetTermSet"
TrackedTermsSet_Name = "TrackedSetTermSet"
TrackedRegexSet_Name = "TrackedRegexSet"
top_term_freq_max_set_cardinality = 20 # Max cardinality of the terms frequences set
oneDay = 60*60*24
top_termFreq_setName_day = ["TopTermFreq_set_day_", 1]
top_termFreq_setName_week = ["TopTermFreq_set_week", 7]
top_termFreq_setName_month = ["TopTermFreq_set_month", 31]
top_termFreq_set_array = [top_termFreq_setName_day,top_termFreq_setName_week, top_termFreq_setName_month]


def refresh_dicos():
    dico_regex = {} 
    dico_regexname_to_redis = {}
    for regex_str in server_term.smembers(TrackedRegexSet_Name):
        dico_regex[regex_str[1:-1]] = re.compile(regex_str[1:-1])
        dico_regexname_to_redis[regex_str[1:-1]] = regex_str

    return dico_regex, dico_regexname_to_redis

if __name__ == "__main__":
    publisher.port = 6380
    publisher.channel = "Script"

    config_section = 'RegexForTermsFrequency'
    p = Process(config_section)

    # REDIS #
    server_term = redis.StrictRedis(
        host=p.config.get("Redis_Level_DB_TermFreq", "host"),
        port=p.config.get("Redis_Level_DB_TermFreq", "port"),
        db=p.config.get("Redis_Level_DB_TermFreq", "db"))

    # FUNCTIONS #
    publisher.info("RegexForTermsFrequency script started")

    #compile the regex
    dico_refresh_cooldown = time.time()
    dico_regex, dico_regexname_to_redis = refresh_dicos()

    message = p.get_from_set()

    # Regex Frequency
    while True:

        if message is not None:
            if time.time() - dico_refresh_cooldown > DICO_REFRESH_TIME:
                dico_refresh_cooldown = time.time()
                dico_regex, dico_regexname_to_redis = refresh_dicos()
                print('dico got refreshed')

            filename = message
            temp = filename.split('/')
            timestamp = calendar.timegm((int(temp[-4]), int(temp[-3]), int(temp[-2]), 0, 0, 0))

            curr_set = top_termFreq_setName_day[0] + str(timestamp)
            content = Paste.Paste(filename).get_p_content()

            #iterate the word with the regex
            for regex_str, compiled_regex in dico_regex.items():
                matched = compiled_regex.search(content)

                if matched is not None: #there is a match
                    print('regex matched {}'.format(regex_str))
                    matched = matched.group(0)
                    # Add in Regex track set only if term is not in the blacklist
                    if matched not in server_term.smembers(BlackListTermsSet_Name):
                        set_name = 'regex_' + dico_regexname_to_redis[regex_str]
                        new_to_the_set = server_term.sadd(set_name, filename)
                        new_to_the_set = True if new_to_the_set == 1 else False

                        #consider the num of occurence of this term
                        regex_value = int(server_term.hincrby(timestamp, dico_regexname_to_redis[regex_str], int(1)))
                        #1 term per paste
                        if new_to_the_set:
                            regex_value_perPaste = int(server_term.hincrby("per_paste_" + str(timestamp), dico_regexname_to_redis[regex_str], int(1)))
                            server_term.zincrby("per_paste_" + curr_set, dico_regexname_to_redis[regex_str], float(1))
                    server_term.zincrby(curr_set, dico_regexname_to_redis[regex_str], float(1))
                else:
                    pass

        else:
            publisher.debug("Script RegexForTermsFrequency is Idling")
            print "sleeping"
            time.sleep(5)
        message = p.get_from_set()
