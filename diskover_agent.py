#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""diskover storage agent
See README.md or https://github.com/shirosaidev/diskover-storage-agent
for more information.

Copyright (C) Chris Park 2019
diskover storage agent is released under the Apache 2.0 license.
See LICENSE for the full license text.
"""

import requests
import os
import time
import random
import warnings


class AgentConnection:
    def __init__(self, hosts=[], port=9999):
        self.hosts = hosts
        self.port = port
        self.r = None
        self.resptime = None
        self.ses = None
        self.host = None


    def connect(self):
        """Sets up requests session and tries to load balance
        requests across hosts in cluster running diskover storage agent
        """
        if len(self.hosts) == 0:
            warnings.warn("hosts not set for AgentConnection")
            return None
        self.host = random.choice(self.hosts)
        self.ses = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=100)
        self.ses.mount('http://', adapter)


    def listdir(self, path):
        """Yields a dirlist set similiar to os.listdir
        """
        starttime = time.time()
        url = 'http://%s:%s%s' % (self.host, self.port, path)
        try:
            self.r = self.ses.get(url)
        except requests.exceptions.RequestException as e:
            warnings.warn(e)
            return
        self.resptime = round(time.time() - starttime, 4)
        dirlist = self.r.text.split("\n")
        dirs = []
        nondirs = []
        for item in dirlist:
            if item in ['../', './', '']:
                continue
            elif item.endswith('/'):  # directory
                dirs.append(item.rstrip('/'))
            elif not item.endswith('*'):  # file
                nondirs.append(item)
        yield path, dirs, nondirs

    def walk(self, top):
        """Yields a recursive dirlist set similiar to os.walk
        """
        for root, dirs, files in self.listdir(top):
            # Yield before recursion
            yield root, dirs, files
            # Recurse into sub-directories
            for d_path in dirs:
                for entry in self.walk(os.path.join(root, d_path)):
                    yield entry


    def status_code(self):
        return self.r.status_code
    

    def content_type(self):
        return self.r.headers['content-type']


    def encoding(self):
        return self.r.encoding


    def text(self):
        return self.r.text


    def last_host(self):
        return self.host


    def last_response_time(self):
        return self.resptime