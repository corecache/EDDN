# coding: utf8
import hashlib
import re
import simplejson

from datetime import datetime, timedelta
from eddn.conf.Settings import Settings
from threading import Lock, Thread
from time import sleep


class DuplicateMessages(Thread):
    max_minutes = Settings.RELAY_DUPLICATE_MAX_MINUTES

    caches = {}

    lock = Lock()

    def __init__(self):
        super(DuplicateMessages, self).__init__()
        self.daemon = True

    def run(self):
        while True:
            sleep(60)
            with self.lock:
                maxTime = datetime.utcnow()

                for key in self.caches.keys():
                    if self.caches[key] + timedelta(minutes=self.max_minutes) < maxTime:
                        del self.caches[key]

    def isDuplicated(self, json):
        with self.lock:
            # Test messages are not duplicate
            if re.search('test', json['$schemaRef'], re.I):
                return False

            # Shallow copy, minus headers
            jsonTest = {
                '$schemaRef': json['$schemaRef'],
                'message': dict(json['message']),
            }

            # Convert starPos to avoid software modification in dupe messages
            if 'StarPos' in jsonTest['message']:
                jsonTest['message']['StarPos'] = [int(round(x * 32)) for x in jsonTest['message']['StarPos']]

            # Prevent Docked event with small difference in distance from start
            if 'DistFromStarLS' in jsonTest['message']:
                jsonTest['message']['DistFromStarLS'] = int(jsonTest['message']['DistFromStarLS'] + 0.5)

            message = simplejson.dumps(jsonTest, sort_keys=True) # Ensure most duplicate messages will get the same key
            key     = hashlib.sha256(message).hexdigest()

            if key not in self.caches:
                self.caches[key] = datetime.utcnow()
                return False
            else:
                self.caches[key] = datetime.utcnow()
                return True
