# Gluster Georep Tools

Collection of Utilities for Gluster Geo-replication

Install Gluster CLI Python bindings using,

```console
$ git clone https://github.com/gluster/glustercli-python.git
$ cd glustercli-python
$ sudo python setup.py install
```

Install all the tools using,

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
usage: gluster-georep-setup [-h] [--force] [--no-color] PRIMARY_VOL SECONDARY

CLI tool to setup Gluster Geo-replication Session between
Primary Gluster Volume to Secondary Gluster Volume.

positional arguments:
  PRIMARY_VOL   Primary Volume Name
  SECONDARY     Secondary, HOSTNAME or root@HOSTNAME::SECONDARY_VOL or
              user@HOSTNAME::SECONDARY_VOL

optional arguments:
  -h, --help  show this help message and exit
  --force     Force
  --no-color  No Terminal Colors
```

Example,

```console
root@server1:/# gluster-georep-setup gvol1 remote1.kadalu::gvol2
Geo-replication session will be established between gvol1 and remote1.kadalu::gvol2
Root password of remote1.kadalu is required to complete the setup. NOTE: Password will not be stored.

root@remote1.kadalu's password:
[    OK] remote1.kadalu is Reachable(Port 22)
[    OK] SSH Connection established root@remote1.kadalu
[    OK] Primary Volume and Secondary Volume are compatible (Version: 7.2)
[    OK] Common secret pub file present at /var/lib/glusterd/geo-replication/common_secret.pem.pub
[    OK] common_secret.pem.pub file copied to remote1.kadalu
[    OK] Primary SSH Keys copied to all Up Secondary nodes
[    OK] Updated Primary SSH Keys to all Up Secondary nodes authorized_keys file
[    OK] Geo-replication Session Established
```

or

```console
root@server1:/# gluster-georep-setup gvol1 geoaccount@remote1.kadalu::gvol2
Geo-replication session will be established between gvol1 and remote1.kadalu::gvol2
Root password of remote1.kadalu is required to complete the setup. NOTE: Password will not be stored.

root@remote1.kadalu's password:
[    OK] remote1.kadalu is Reachable(Port 22)
[    OK] SSH Connection established root@remote1.kadalu
[    OK] Primary Volume and Secondary Volume are compatible (Version: 7.2)
[    OK] Common secret pub file present at /var/lib/glusterd/geo-replication/common_secret.pem.pub
[    OK] common_secret.pem.pub file copied to remote1.kadalu
[    OK] Primary SSH Keys copied to all Up Secondary nodes
[    OK] Updated Primary SSH Keys to all Up Secondary nodes authorized_keys file
[    OK] Geo-replication Session Established
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
                        [<secondary_user>@]<secondary_host>::<secondary_vol>, Example:
                        geoaccount@secondary_node1::myvol or secondary_node1::myvol in
                        case of root user

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
+---------------------------+---------+-----------------+-------------------+---------------------+------------+-----------------+----------------------+
|      PRIMARY              | STATUS  |   CRAWL STATUS  | SECONDARY NODE    |     LAST SYNCED     | CHKPT TIME | CHKPT COMPLETED | CHKPT COMPLETION TIME |
+---------------------------+---------+-----------------+-------------------+---------------------+------------+-----------------+----------------------+
| server1.kadalu:/bricks/b1 | Active  | Changelog Crawl |    remote1.kadalu | 2021-05-14 08:34:40 |    N/A     |       N/A       |          N/A         |
| server2.kadalu:/bricks/b2 | Passive | N/A             |    remote2.kadalu | N/A                 |    N/A     |       N/A       |          N/A         |
| server3.kadalu:/bricks/b3 | Passive | N/A             |    remote2.kadalu | N/A                 |    N/A     |       N/A       |          N/A         |
+---------------------------+---------+-----------------+-------------------+---------------------+------------+-----------------+----------------------+
```
