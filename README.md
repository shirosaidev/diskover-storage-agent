# diskover-storage-agent

A simple http server for running on storage nodes to return dir lists. Can be run on multiple storage nodes for load balancing requests.

### Requirements
- Python 2.6+ (no other dependencies)


### Usage

Copy diskover_storage_agent.py to each node (for example stornode1, stornode2) on your storage cluster.

To start the http server (storage agent) on each node, run:

`$ python diskover_storage_agent.py -l 0.0.0.0 -p 9999 -c 5 -r /ifs/data /mnt/isilon`

```
Usage: diskover_storage_agent.py [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -l LISTEN, --listen=LISTEN
                        IP address for diskover storage agent to listen on
                        (default: 0.0.0.0)
  -p PORT, --port=PORT  Port for diskover storage agent (default: 9999)
  -c MAXCONNECTIONS, --maxconnections=MAXCONNECTIONS
                        Maximum number of connections (default: 5)
  -r PATH PATH, --replacepath=PATH PATH
                        Replace paths from remote to local,
                        example: -r /mnt/share/ /ifs/data/
```

Example to access the http agents in python import diskover_agent.py module:

```
>>> import diskover_agent
>>> c = diskover_agent.AgentConnection(hosts=['stornode1', 'stornode2'])
>>> c.get_dir_list('/mnt/isilon/somedir')
('/mnt/isilon/somedir', ['subdir1', 'subdir2'], ['file1.ext', 'file2.ext'])
>>> c.get_last_host()
stornode1
>>> c.get_last_response_time()
0.0326
>>> c.get_dir_list('/mnt/isilon/someotherdir')
('/mnt/isilon/someotherdir', ['subdira', 'subdirb'], ['filea.ext', 'fileb.ext'])
>>> c.get_last_host()
stornode2
>>> c.get_last_response_time()
0.0214
```

Example using curl:

```
$ curl http://stornode1:9999/mnt/isilon/somedir
./
../
file1.ext
file2.ext
somesymlink.ext*
subdir1/
subdir2/
```
