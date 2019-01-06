#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""diskover storage agent
See README.md or https://github.com/shirosaidev/diskover-storage-agent
for more information.

Copyright (C) Chris Park 2019
diskover storage agent is released under the Apache 2.0 license.
See LICENSE for the full license text.
"""

import os
import sys
import socket
import subprocess
from optparse import OptionParser
try:
    import queue as Queue
except ImportError:
    import Queue
import threading
import time
import logging
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

version = '0.1.0'
__version__ = version

# socket buffer size
BUFF = 1024

IS_PY3 = sys.version_info >= (3, 0)
if IS_PY3:
	unicode = str


parser = OptionParser(version="diskover storage agent v % s" % version)
parser.add_option("-l", "--listen", default="0.0.0.0", type=str,
					help="IP address for diskover storage agent to listen on (default: 0.0.0.0)")
parser.add_option("-p", "--port", metavar="PORT", default=9999, type=int,
					help="Port for diskover storage agent (default: 9999)")
parser.add_option("-c", "--maxconnections", default=5, type=int,
					help="Maximum number of connections (default: 5)")
parser.add_option("-r", "--replacepath", nargs=2, metavar="PATH PATH",
                    help="Replace paths from remote to local, \
                    example: -r /mnt/share/ /ifs/data/")
(options, args) = parser.parse_args()
options = vars(options)

if not options['replacepath']:
	parser.error("missing required options, use -h for help")

IP = options['listen']
PORT =  options['port']
MAX_CONNECTIONS =  options['maxconnections']
ROOTDIR_LOCAL = unicode(options['replacepath'][1])
ROOTDIR_REMOTE = unicode(options['replacepath'][0])
# remove any trailing slash from paths
if ROOTDIR_LOCAL != '/':
	ROOTDIR_LOCAL = ROOTDIR_LOCAL.rstrip(os.path.sep)
if ROOTDIR_REMOTE != '/':
	ROOTDIR_REMOTE = ROOTDIR_REMOTE.rstrip(os.path.sep)


def send_ls_output(threadnum, path, clientsock, addr):
    """This is the send ls output function.
    It gets a directory from the listener socket and returns
    directory listing to client using ls.
    """

    try:
        starttime = time.time()
        # translate path from remote to local
        localpath = path.replace(ROOTDIR_REMOTE, ROOTDIR_LOCAL)
        # run subprocess and get output
        logger.info("[thread-%s]: Running ls -FAf %s for %s" % (threadnum, localpath, addr))
        try:
            output = subprocess.check_output(['ls', '-FAf', localpath])

            elapsedtime = round(time.time() - starttime, 4)
            logger.info("[thread-%s]: Got ls %s in %s seconds" % (threadnum, localpath, elapsedtime))

            # send ls output to client
            logger.info("[thread-%s]: Sending dirlist for %s to %s" % (threadnum, localpath, addr))
            #clientsock.send(output)
            response = "HTTP/1.1 200 OK\n" \
                        +"Content-Type: text/plain\n" \
                        +"\n" \
                        +output.decode('utf-8')
            clientsock.send(response.encode('utf-8'))
        except subprocess.CalledProcessError as e:
            logger.info("[thread-%s]: Exception getting %s (%s)" % (threadnum, path, e))
            response = "HTTP/1.1 404 Not Found\n" \
                        +"Content-Type: text/plain\n" \
                        +"\n" \
                        +"ls: %s: No such file or directory\n" % path
            clientsock.send(response.encode('utf-8'))
            pass

    except socket.error as e:
        logger.error("[thread-%s]: Socket error (%s)" % (threadnum, e))
        pass


def socket_thread_handler(threadnum, q):
    """This is the socket thread handler function.
    It processes the dirlist request sent from client.
    """

    while True:
        try:
            c = q.get()
            clientsock, addr = c
            data = clientsock.recv(BUFF)
            data = data.decode('utf-8')
            #logger.info(data)
            if not data:
                q.task_done()
                # close connection to client
                clientsock.close()
                logger.info("[thread-%s]: %s closed connection" % (threadnum, addr))
                continue
            # grab path from header sent by curl PUT /somepath HTTP/1.1
            path = data.split('\r\n')[0].split(" ")[1]
            # decode url to path
            path = unquote(path)
            logger.info("[thread-%s]: Got dirlist request from %s" % (threadnum, addr))
            # get dirlist from json data
            send_ls_output(threadnum, path, clientsock, addr)

            q.task_done()
            # close connection to client
            clientsock.close()
            logger.info("[thread-%s]: %s closed connection" % (threadnum, addr))

        except socket.error as e:
            q.task_done()
            logger.error("[thread-%s]: Socket error (%s)" % (threadnum, e))
            # close connection to client
            clientsock.close()
            logger.info("[thread-%s]: %s closed connection" % (threadnum, addr))
            pass


def main():
    """This is the start socket server function.
    It opens a socket and waits for dirlist requests.
    """
    global logger

    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logging.addLevelName(
        logging.INFO, "\033[1;32m%s\033[1;0m"
                      % logging.getLevelName(logging.INFO))
    logging.addLevelName(
        logging.WARNING, "\033[1;31m%s\033[1;0m"
                         % logging.getLevelName(logging.WARNING))
    logging.addLevelName(
        logging.ERROR, "\033[1;41m%s\033[1;0m"
                       % logging.getLevelName(logging.ERROR))
    logging.addLevelName(
        logging.DEBUG, "\033[1;33m%s\033[1;0m"
                       % logging.getLevelName(logging.DEBUG))
    logformatter = '%(asctime)s [%(levelname)s][%(name)s] %(message)s'
    loglevel = logging.INFO
    logging.basicConfig(format=logformatter, level=loglevel)

    # Queue for socket threads
    q = Queue.Queue(maxsize=MAX_CONNECTIONS)

    try:
        # create TCP socket object
        serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind to port
        serversock.bind((IP, PORT))
        # start listener
        serversock.listen(MAX_CONNECTIONS)

        # set up the threads and start them
        for i in range(MAX_CONNECTIONS):
            # create thread
            t = threading.Thread(target=socket_thread_handler, args=(i, q,))
            t.daemon = True
            t.start()
        
        banner = """\033[31m
  __               __
 /\ \  __         /\ \\
 \_\ \/\_\    ____\ \ \/'\\     ___   __  __     __   _ __     //
 /'_` \/\ \  /',__\\\ \ , <    / __`\/\ \/\ \  /'__`\/\`'__\\  ('>
/\ \L\ \ \ \/\__, `\\\ \ \\\`\ /\ \L\ \ \ \_/ |/\  __/\ \ \/   /rr
\ \___,_\ \_\/\____/ \ \_\ \_\ \____/\ \___/ \ \____\\\ \\_\\  *\))_
 \/__,_ /\/_/\/___/   \/_/\/_/\/___/  \/__/   \/____/ \\/_/
				  
	  Storage Dirlist Agent v%s
	  
	  https://shirosaidev.github.io/diskover
	  "Finding light in the darkness."
	  Support diskover on Patreon or PayPal :)\033[0m
		""" % version

        print(banner)

        logger.info(" * Listening on http://%s:%s (ctrl-c to shutdown)" % (str(IP), str(PORT)))
        while True:
            # establish connection
            clientsock, addr = serversock.accept()
            logger.info("Got a connection from %s" % str(addr))
            # add client to list
            client = (clientsock, addr)
            # add task to Queue
            q.put(client)

    except socket.error as e:
        serversock.close()
        logger.error("Error opening socket (%s)" % e)
        sys.exit(1)

    except KeyboardInterrupt:
        print('\nCtrl-c keyboard interrupt received, shutting down...')
        q.join()
        serversock.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
