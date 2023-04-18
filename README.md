# Gluster Georep Tools

Collection of Utilities for Gluster Geo-replication

Install by running the following pip command

```
$ pip install gluster-georep-tools
```

or install by cloning the repository

```console
$ git clone https://github.com/aravindavk/gluster-georep-tools.git
$ cd gluster-georep-tools
$ sudo python setup.py install
```

## List of Tools
- [gluster-georep-setup](#gluster-georep-setup)
- [gluster-georep-status](#gluster-georep-status)

### gluster-georep-setup

Utility to setup Geo-replication easily.

Usage:

```console
$ gluster-georep-setup -h
usage: gluster-georep-setup [-h] [--secondary-user SECONDARY_USER] [--force] [--no-color] PRIMARY_VOL SECONDARY

CLI tool to setup Gluster Geo-replication Session between
Primary Gluster Volume to Secondary Gluster Volume.

positional arguments:
  PRIMARY_VOL           Primary Volume Name
  SECONDARY             Secondary, HOSTNAME or HOSTNAME::SECONDARY_VOL

options:
  -h, --help            show this help message and exit
  --secondary-user SECONDARY_USER
                        Admin user in one of the node of the secondary cluster
  --force               Force
  --no-color            No Terminal Colors
```

Example,

```console
$ sudo gluster-georep-setup vol1 server2::vol2 --secondary-user ubuntu
Geo-replication session will be established between vol1 and server2::vol2
ubuntu@server2 password is required to complete the setup. NOTE: Password will not be stored.

ubuntu@server2's password:
[	OK] server2 is Reachable(Port 22)
[	OK] SSH Connection established ubuntu@server2
[	OK] Primary Volume and Secondary Volume are compatible (Version: 11.0)
[	OK] Common secret pub file present at /var/lib/glusterd/geo-replication/common_secret.pem.pub
[	OK] common_secret.pem.pub file copied to server2
[	OK] Primary SSH Keys copied to all Up Secondary nodes
[	OK] Updated Primary SSH Keys to all Up Secondary nodes authorized_keys file
[	OK] Geo-replication Session Established
```

### gluster-georep-status

Tool to check Geo-rep status. Reasons to use this tool instead of gluster CLI for status are

- Nodes will be displayed in the same order as in Volume info
- Offline nodes are shown with Offline as status
- Status output from different sessions are not mixed.
- Filters are available(Ex: --with-status=active, --with-crawl-status=changelog, --with-status=faulty etc)

Usage:

```console
$ gluster-georep-status -h
usage: gluster-georep-status [-h] [--with-status WITH_STATUS]
                             [--with-crawl-status WITH_CRAWL_STATUS]
                             [primary_vol] [secondary]

Gluster Geo-replication Status

positional arguments:
  primary_vol           Primary Volume Name
  secondary             Secondary details.
                        <secondary_host>::<secondary_vol>, Example:
                        secondary_node1::myvol

optional arguments:
  -h, --help            show this help message and exit
  --with-status WITH_STATUS
                        Show only nodes with matching Status
  --with-crawl-status WITH_CRAWL_STATUS
                        Show only nodes with matching Crawl Status
```

Example,

```console
root@server1:/# gluster-georep-status
root@server1:/# gluster-georep-status gvol1
root@server1:/# gluster-georep-status gvol1 remote1.kadalu::gvol2
root@server1:/# gluster-georep-status --with-status=active
```

Example output with two sessions

```console
root@server1:/# gluster-georep-status
SESSION: gvol1 ==> remote1.kadalu::gvol2
+---------------------------+---------+-----------------+-------------------+---------------------+
|      PRIMARY              | STATUS  |   CRAWL STATUS  | SECONDARY NODE    |     LAST SYNCED     |
+---------------------------+---------+-----------------+-------------------+---------------------+
| server1.kadalu:/bricks/b1 | Active  | Changelog Crawl |    remote1.kadalu | 2021-05-14 08:34:40 |
| server2.kadalu:/bricks/b2 | Passive | N/A             |    remote2.kadalu | N/A                 |
| server3.kadalu:/bricks/b3 | Passive | N/A             |    remote2.kadalu | N/A                 |
+---------------------------+---------+-----------------+-------------------+---------------------+
```
