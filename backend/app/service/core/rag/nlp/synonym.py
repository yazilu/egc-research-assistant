#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import json
import os
import time
import re
from nltk.corpus import wordnet
from service.core.api.utils.file_utils import get_project_base_directory


class Dealer:
    def __init__(self, redis=None):

        self.lookup_num = 100000000
        self.load_tm = time.time() - 1000000
        self.dictionary = {}
        path = os.path.join(get_project_base_directory(), "rag/res", "synonym.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as synonym_file:
                    self.dictionary = json.load(synonym_file)
            except (OSError, json.JSONDecodeError) as exc:
                logging.warning("Unable to load synonym dictionary %s: %s", path, exc)
        else:
            logging.info("No static synonym dictionary configured; synonym expansion starts empty.")

        if not redis:
            logging.info("Realtime synonym updates are disabled because Redis is not configured.")

        self.redis = redis
        self.load()

    def load(self):
        if not self.redis:
            return

        if self.lookup_num < 100:
            return
        tm = time.time()
        if tm - self.load_tm < 3600:
            return

        self.load_tm = time.time()
        self.lookup_num = 0
        d = self.redis.get("kevin_synonyms")
        if not d:
            return
        try:
            d = json.loads(d)
            self.dictionary = d
        except Exception as e:
            logging.error("Fail to load synonym!" + str(e))

    def lookup(self, tk):
        if re.match(r"[a-z]+$", tk):
            res = list(set([re.sub("_", " ", syn.name().split(".")[0]) for syn in wordnet.synsets(tk)]) - set([tk]))
            return [t for t in res if t]

        self.lookup_num += 1
        self.load()
        res = self.dictionary.get(re.sub(r"[ \t]+", " ", tk.lower()), [])
        if isinstance(res, str):
            res = [res]
        return res


if __name__ == '__main__':
    dl = Dealer()
    print(dl.dictionary)
