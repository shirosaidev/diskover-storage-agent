# diskover-storage-agent

A simple http server for running on storage nodes to return dir lists. Can be run on multiple storage nodes for load balancing requests.

### Requirements
- Python 2.6+
- scandir.py (in repo, for server only)
- requests python module (only needed for client diskover_agent module)

### Usage

Copy `diskover_storage_agent.py` and `scandir.py` to each node (for example stornode1, stornode2) on your storage cluster.

To start the http server (storage agent) on each node, run:

```
$ python diskover_storage_agent.py -r /ifs/data /mnt/isilon
```

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
                        Maximum number of connections (default: 50)
  -r PATH PATH, --replacepath=PATH PATH
                        Replace paths from remote to local,
                        example: -r /mnt/share/ /ifs/data/
  -v, --verbose         Increase verbosity (specify multiple times for more)
```

Example to access the http agents in python import diskover_agent.py module:

```
>>> import diskover_agent
>>> hostlist = ['stornode1', 'stornode2']
>>> c = diskover_agent.AgentConnection(hosts=hostlist)
>>> c.hostlist()
['stornode1', 'stornode2']
>>> c.connect()
>>> c.conn_host()
stornode1
>>> c.listdir('/mnt/isilon/somedir')
('/mnt/isilon/somedir', ['subdir1', 'subdir2'], ['file1.ext', 'file2.ext'])
>>> c.response_time()
0.0198
>>> c.connect()
>>> c.conn_host()
stornode2
>>> c.listdir('/mnt/isilon/someotherdir')
('/mnt/isilon/someotherdir', ['subdira', 'subdirb'], ['filea.ext', 'fileb.ext'])
>>> c.response_time()
0.0182
>>> from diskover_agent import parallel_walk as pwalk
>>> pwalk('/mnt/isilon/somedir', workers=40, hosts=hostlist)
<generator object parallel_walk at 0x1038869b0>
for root, dirs, files in pwalk('/mnt/isilon/somedir', workers=40, hosts=hostlist):
...     print(root, dirs, files)
('/mnt/isilon/somedir', ['subdir1', 'subdir2'], ['file1.ext', 'file2.ext'])
('/mnt/isilon/somedir/subdir1', [], ['file.ext'])
```

Example using curl:

```
$ curl http://stornode1:9999/mnt/isilon/somedir
file1.ext
file2.ext
subdir1/
subdir2/
```
