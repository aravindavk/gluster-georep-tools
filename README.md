# Gluster Georep Tools
Collection of Utilities for Gluster Geo-replication

Install Gluster CLI Python bindings using,

    git clone https://github.com/gluster/glustercli-python.git
    cd glustercli-python
    sudo python setup.py install

Install all the tools using,

    git clone https://github.com/aravindavk/gluster-georep-tools.git
    cd gluster-georep-tools
    sudo python setup.py install

## gluster-georep-setup
Utility to setup Geo-replication easily.

Usage:

    usage: gluster-georep-setup [-h] [--force] [--no-color] MASTERVOL SLAVE
     
    CLI tool to setup Gluster Geo-replication Session between
    Master Gluster Volume to Slave Gluster Volume.
     
    positional arguments:
      MASTERVOL   Master Volume Name
      SLAVE       Slave, HOSTNAME or root@HOSTNAME::SLAVEVOL or
                  user@HOSTNAME::SLAVEVOL
     
    optional arguments:
      -h, --help  show this help message and exit
      --force     Force
      --no-color  No Terminal Colors

Example,

    sudo gluster-georep-setup gv1 fvm1::gv2

or

    sudo gluster-georep-setup gv1 geoaccount@fvm1::gv2

![gluster-georep-setup in Action](https://github.com/aravindavk/gluster-georep-tools/blob/master/screenshots/gluster-georep-setup.png)

## gluster-georep-status
Tool to check Geo-rep status. Reasons to use this tool instead of gluster CLI for status are

- Nodes will be displayed in the same order as in Volume info
- Offline nodes are shown with Offline as status
- Status output from different sessions are not mixed.
- Filters are available(Ex: --with-status=active, --with-crawl-status=changelog, --with-status=faulty etc)

Usage:

    usage: gluster-georep-status [-h] [--with-status WITH_STATUS]
                                 [--with-crawl-status WITH_CRAWL_STATUS]
                                 [mastervol] [slave]
     
    Gluster Geo-replication Status
     
    positional arguments:
      mastervol             Master Volume Name
      slave                 Slave details.
                            [<slave_user>@]<slave_host>::<slave_vol>, Example:
                            geoaccount@slavenode1::myvol or slavenode1::myvol in
                            case of root user
     
    optional arguments:
      -h, --help            show this help message and exit
      --with-status WITH_STATUS
                            Show only nodes with matching Status
      --with-crawl-status WITH_CRAWL_STATUS
                            Show only nodes with matching Crawl Status

Example,

    gluster-georep-status
    gluster-georep-status gv1
    gluster-georep-status gv1 fvm1::gv2
    gluster-georep-status --with-status=active

Example output with two sessions

    SESSION: gv1 ==> fvm1::gv2
    +-----------------+--------+-----------------+------------+---------------------+------------+-----------------+-----------------------+
    |      MASTER     | STATUS |   CRAWL STATUS  | SLAVE NODE |     LAST SYNCED     | CHKPT TIME | CHKPT COMPLETED | CHKPT COMPLETION TIME |
    +-----------------+--------+-----------------+------------+---------------------+------------+-----------------+-----------------------+
    | fvm1:/bricks/b1 | Active | Changelog Crawl |    fvm1    | 2016-11-14 08:34:40 |    N/A     |       N/A       |          N/A          |
    | fvm1:/bricks/b2 | Active | Changelog Crawl |    fvm1    | 2016-11-14 08:32:21 |    N/A     |       N/A       |          N/A          |
    +-----------------+--------+-----------------+------------+---------------------+------------+-----------------+-----------------------+
     
    SESSION: gv1 ==> geoaccount@fvm1::gv3
    +-----------------+---------+--------------+------------+-------------+------------+-----------------+-----------------------+
    |      MASTER     |  STATUS | CRAWL STATUS | SLAVE NODE | LAST SYNCED | CHKPT TIME | CHKPT COMPLETED | CHKPT COMPLETION TIME |
    +-----------------+---------+--------------+------------+-------------+------------+-----------------+-----------------------+
    | fvm1:/bricks/b1 | Stopped |     N/A      |    N/A     |     N/A     |    N/A     |       N/A       |          N/A          |
    | fvm1:/bricks/b2 | Stopped |     N/A      |    N/A     |     N/A     |    N/A     |       N/A       |          N/A          |
    +-----------------+---------+--------------+------------+-------------+------------+-----------------+-----------------------+

