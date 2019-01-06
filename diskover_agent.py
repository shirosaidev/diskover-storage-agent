#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""diskover - Elasticsearch file system crawler
diskover is a file system crawler that index's
your file metadata into Elasticsearch.
See README.md or https://github.com/shirosaidev/diskover
for more information.

Copyright (C) Chris Park 2017-2018
diskover is released under the Apache 2.0 license. See
LICENSE for the full license text.
"""

import time
import requests
import random
import warnings


class AgentConnection:
    def __init__(self, hosts=[], port=9999):
        self.hosts = hosts
        self.port = port
        self.r = None
        self.last_host = None
        self.last_response_time = None


    def load_balanced_conn(self, path):
        """Returns a url for requests and tries to load balance
        requests across hosts in cluster running diskover storage agent
        """
        if len(self.hosts) == 0:
            warnings.warn("hosts not set for AgentConnection")
            return None
        i = random.randint(0, len(self.hosts)-1)
        url = 'http://%s:%s%s' % (self.hosts[i], self.port, path)
        self.last_host = self.hosts[i]
        return url

    def get_dir_list(self, path):
        """Returns a dirlist set similiar to scandir
        """
        url = self.load_balanced_conn(path)
        starttime = time.time()
        try:
            self.r = requests.get(url)
        except requests.exceptions.RequestException as e:
            warnings.warn(e)
            return None
        self.last_response_time = round(time.time() - starttime, 4)
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
        return (path, dirs, nondirs)

    def get_status_code(self):
        return self.r.status_code
    
    def get_content_type(self):
        return self.r.headers['content-type']
        
    def get_encoding(self):
        return self.r.encoding

    def get_text(self):
        return self.r.text

    def get_last_host(self):
        return self.last_host

    def get_last_response_time(self):
        return self.last_response_time