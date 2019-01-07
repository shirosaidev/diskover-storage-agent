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
import sys
import time
import random
import warnings
import multiprocessing


IS_PY3 = sys.version_info >= (3, 0)
if IS_PY3:
	unicode = str


class AgentConnection:
    def __init__(self, hosts=[], port=9999):
        self.hosts = hosts
        self.port = port
        self.r = None
        self.resptime = None
        self.ses = None
        self.host = None

        if not self.hosts:
            warnings.warn("hosts list empty for AgentConnection")
            return None


    def connect(self):
        """Sets up requests session and tries to load balance
        requests across hosts in cluster running diskover storage agent
        """
        self.host = self.load_balance()
        self.ses = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=100)
        self.ses.mount('http://', adapter)


    def load_balance(self):
        host = random.choice(self.hosts)
        return host


    def listdir(self, path, *args):
        """Adds subdirs to walk queue
        """
        pwalk = False
        if args:  # parallel_walk
            q = args[0]
            q_res = args[1]
            val = args[2]
            lock = args[3]
            pwalk = True
        starttime = time.time()
        url = 'http://%s:%s%s' % (self.host, self.port, path)
        try:
            self.r = self.ses.get(url)
        except requests.exceptions.RequestException as e:
            warnings.warn(str(e))
            return None
        if self.r.status_code == 404:
            warnings.warn("404 No such file or directory")
            return None
        self.resptime = round(time.time() - starttime, 4)
        dirlist = self.r.text.split("\n")
        if dirlist[-1] == "":
            dirlist.pop()
        dirs = []
        nondirs = []
        for item in dirlist:
            if item.endswith('/'):  # directory
                d_name = item.rstrip('/')
                if pwalk:
                    add_to_q(q, q_res, val, lock, os.path.join(path, d_name))
                dirs.append(d_name)
            else:  # file
                nondirs.append(item)
        return path, dirs, nondirs


    def status_code(self):
        return self.r.status_code
    

    def content_type(self):
        return self.r.headers['content-type']


    def encoding(self):
        return self.r.encoding


    def text(self):
        return self.r.text


    def conn_host(self):
        return self.host

    
    def hostlist(self):
        return self.hosts


    def response_time(self):
        return self.resptime


def worker(q, q_res, val, lock, hosts):
    c = AgentConnection(hosts=hosts)
    c.connect()
    while True:
        item = q.get(True)
        ret_data = c.listdir(item, q, q_res, val, lock)
        q_res.put(ret_data)
        with lock:
            val.value -= 1


def add_to_q(q, q_res, val, lock, item):
    q.put(item)
    with lock:
        val.value += 1


def parallel_walk(top=unicode("."), workers=40, hosts=[]):
    if not hosts:
        warnings.warn("hosts list empty")
        return
    q = multiprocessing.Queue()
    q_res = multiprocessing.Queue()
    q_len = multiprocessing.Value('i', 0)
    q_lock = multiprocessing.Lock()

    pool = multiprocessing.Pool(workers, worker, (q, q_res, q_len, q_lock, hosts))

    add_to_q(q, q_res, q_len, q_lock, top)

    while q_len.value > 0:
        item = q_res.get(True)
        yield item