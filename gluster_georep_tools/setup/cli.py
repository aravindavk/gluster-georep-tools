# -*- coding: utf-8 -*-
"""
    georepsetup.cli.py
    :copyright: (c) 2015 by Aravinda VK
    :license: MIT, see LICENSE for more details.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from contextlib import contextmanager
import getpass
import os
import socket
import subprocess
import sys
import tempfile

import paramiko

PROG_DESCRIPTION = """
CLI tool to setup Gluster Geo-replication Session between
Master Gluster Volume to Slave Gluster Volume.
"""
BUFFER_SIZE = 104857600  # Considering buffer_size 100MB
SESSION_MOUNT_LOG_FILE = ("/var/log/glusterfs/geo-replication"
                          "/georepsetup.mount.log")
SYMBOLS = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
DEFAULT_GLUSTERD_WORKDIR = "/var/lib/glusterd"
USE_CLI_COLOR = True


class COLORS:
    """
    Terminal Colors
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    ORANGE = "\033[33m"
    NOCOLOR = "\033[0m"


def human_readable_size(num):
    """
    To show size as 100K, 100M, 10G instead of
    showing in bytes.
    """
    for s in reversed(SYMBOLS):
        power = SYMBOLS.index(s)+1
        if num >= 1024**power:
            value = float(num) / (1024**power)
            return '%.1f%s' % (value, s)

    # if size less than 1024 or human readable not required
    return '%s' % num


def get_number_of_files(path):
    """
    Use find command to count the number of files present in
    given path. Excluding .trashcan directory.
    Ref: $GLUSTER_SRC/geo-replication/src/gverify.sh
    """
    cmd = ["find", path,
           "-maxdepth", "1",
           "-path", os.path.join(path, ".trashcan"),
           "-prune", "-o", "-path", path, "-o", "-print0", "-quit"]
    return execute(cmd,
                   failure_msg="Unable to count number of files "
                   "in Slave Volume")


def cleanup(hostname, volname, mnt):
    """
    Unmount the Volume and Remove the temporary directory
    """
    execute(["umount", mnt],
            failure_msg="Unable to Unmount Gluster Volume "
            "{0}:{1}(Mounted at {2})".format(hostname, volname, mnt))
    execute(["rmdir", mnt],
            failure_msg="Unable to Remove temp directory "
            "{0}".format(mnt))


@contextmanager
def glustermount(hostname, volname):
    """
    Context manager for Mounting Gluster Volume
    Use as
        with glustermount(HOSTNAME, VOLNAME) as MNT:
            # Do your stuff
    Automatically unmounts it in case of Exceptions/out of context
    """
    mnt = tempfile.mkdtemp(prefix="georepsetup_")
    execute(["glusterfs",
             "--xlator-option=\"*dht.lookup-unhashed=off\"",
             "--volfile-server", hostname,
             "--volfile-id", volname,
             "-l", SESSION_MOUNT_LOG_FILE,
             "--client-pid=-1",
             mnt],
            failure_msg="Unable to Mount Gluster Volume "
            "{0}:{1}".format(hostname, volname))
    if os.path.ismount(mnt):
        yield mnt
    else:
        output_notok("Unable to Mount Gluster Volume "
                     "{0}:{1}".format(hostname, volname))
    cleanup(hostname, volname, mnt)


def is_port_enabled(hostname, port):
    """
    To check if a port is enabled or not. For example
    To check ssh port is enabled or not,
        is_port_enabled(HOSTNAME, 22)

    To see glusterd port is enabled,
        is_port_enabled(HOSTNAME, 24007)
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((hostname, port))
        enabled = True
    except socket.error:
        enabled = False

    s.close()
    return enabled


def color_txt(txt, color):
    """
    Adds the color requested and returns the text which
    is ready to display
    """
    return "%s%s%s" % (color,
                       txt,
                       COLORS.NOCOLOR)


def output_ok(msg):
    """
    Success Message handler.
    """
    pfx = color_txt("[    OK]", COLORS.GREEN) if USE_CLI_COLOR else "[    OK]"
    sys.stdout.write("%s %s\n" % (pfx, msg))


def output_warning(msg, color=True):
    """
    Warning message handler.
    """
    pfx = color_txt("[  WARN]", COLORS.ORANGE) if USE_CLI_COLOR else "[  WARN]"
    sys.stdout.write("%s %s\n" % (pfx, msg))


def output_notok(msg, err="", exitcode=1, color=True):
    """
    Failure message handler. Exits after writing to stderr.
    """
    pfx = color_txt("[NOT OK]", COLORS.RED) if USE_CLI_COLOR else "[NOT OK]"
    sys.stderr.write("%s %s\n%s\n" % (pfx, msg, err))
    sys.exit(exitcode)


def execute(cmd, success_msg="", failure_msg="", exitcode=-1):
    """
    Generic wrapper to execute the CLI commands. Returns Output if success.
    On success it can print message in stdout if specified.
    On failure, exits after writing to stderr.
    """
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        if success_msg:
            output_ok(success_msg)
        return out
    else:
        err_msg = err if err else out
        output_notok(failure_msg, err=err_msg, exitcode=exitcode)


def get_glusterd_workdir():
    """
    Command to get Glusterd working dir. If failed returns the
    default directory /var/lib/glusterd
    """
    p = subprocess.Popen(["gluster", "system::", "getwd"],
                         stdout=subprocess.PIPE)

    out, _ = p.communicate()

    if p.returncode == 0:
        return out.strip()
    else:
        return DEFAULT_GLUSTERD_WORKDIR


def check_host_reachable(slavehost):
    """
    Check if SSH port is open for given slavehost
    """
    if is_port_enabled(slavehost, 22):
        output_ok("{0} is Reachable(Port 22)".format(slavehost))
    else:
        output_notok("{0} is Not Reachable(Port 22)".format(slavehost))


def ssh_initialize(slavehost, passwd):
    """
    Initialize the SSH connection
    """
    ssh = paramiko.SSHClient()
    try:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(slavehost, username="root", password=passwd)
        output_ok("SSH Connection established root@{0}".format(slavehost))
    except paramiko.ssh_exception.AuthenticationException as e:
        output_notok("Unable to establish SSH connection "
                     "to root@{0}:\n{1}".format(slavehost, e))

    return ssh


def compare_gluster_versions(ssh):
    """
    Collect Master version by directly executing CLI command, get Slave version
    via SSH command execution
    """
    # Collect Gluster Version from Master
    master_version = execute(["gluster", "--version"],
                             failure_msg="Failed to get Gluster version "
                             "from Master")
    master_version = master_version.split()[1]

    # Collect Gluster Version from Slave
    stdin, stdout, stderr = ssh.exec_command("gluster --version")
    rc = stdout.channel.recv_exit_status()
    if rc != 0:
        output_notok("Unable to get Slave Gluster Version")

    slave_version = stdout.readline().split()[1]

    # Check for Version mismatch
    if master_version == slave_version:
        output_ok("Master Volume and Slave Volume are "
                  "compatible (Version: {0})".format(master_version))
    else:
        output_notok("Master Volume({0}) and Slave Volume({1}) "
                     "versions not Compatible".format(master_version,
                                                      slave_version))


def compare_disk_sizes(args, slavehost, slavevol):
    """
    Compare the disk sizes and available sizes. Also
    Check Slave volume is empty or not
    """
    master_disk_size = None
    slave_disk_size = None
    master_used_size = None
    slave_used_size = None

    with glustermount("localhost", args.mastervol) as mnt:
        data = os.statvfs(mnt)
        master_disk_size = data.f_blocks * data.f_bsize
        master_used_size = ((data.f_blocks - data.f_bavail) *
                            data.f_bsize)

    with glustermount(slavehost, slavevol) as mnt:
        if get_number_of_files(mnt):
            if not args.force:
                cleanup(slavehost, slavevol, mnt)
                output_notok("{0}::{1} is not empty. Please delete existing "
                             "files in {0}::{1} and retry, or use --force to "
                             "continue without deleting the existing "
                             "files.".format(slavehost, slavevol))
            else:
                output_warning("{0}::{1} is not empty.".format(slavehost,
                                                               slavevol))
        data = os.statvfs(mnt)
        slave_disk_size = data.f_blocks * data.f_bsize
        slave_used_size = ((data.f_blocks - data.f_bavail) *
                           data.f_bsize)

    if master_disk_size is None or master_used_size is None:
        msg = "Unable to get Disk size and Used size of Master Volume"
        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)

    if slave_disk_size is None or slave_used_size is None:
        msg = "Unable to get Disk size and Used size of Slave Volume"
        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)

    if slave_disk_size < master_disk_size:
        msg = ("Total disk size of master({0}) is greater "
               "than disk size of slave({1})".format(
                   human_readable_size(master_disk_size),
                   human_readable_size(slave_disk_size)))
        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)

    effective_master_used_size = master_used_size + BUFFER_SIZE
    slave_available_size = slave_disk_size - slave_used_size
    master_available_size = master_disk_size - effective_master_used_size

    if slave_available_size < master_available_size:
        msg = ("Total available size of master({0}) is greater "
               "than available size of slave({1})".format(
                   human_readable_size(master_available_size),
                   human_readable_size(slave_available_size)))

        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)


def run_gsec_create(georep_dir):
    """
    gsec_create command to generate pem keys in all the master nodes
    and collect all pub keys to single node
    """
    execute(["gluster", "system::", "execute", "gsec_create"],
            success_msg="Common secret pub file present at "
            "{0}/common_secret.pem.pub".format(georep_dir),
            failure_msg="Common secret pub file generation failed")


def copy_to_main_slave_node(ssh, args, slavehost, georep_dir, pubfile):
    """
    Copy common_secret.pem.pub file to Main Slave node
    """
    # Copy common_secret.pem.pub file to Main Slave node
    ftp = ssh.open_sftp()
    ftp.put("{georep_dir}/common_secret.pem.pub".format(georep_dir=georep_dir),
            "{georep_dir}/{pubfile}".format(
                georep_dir=georep_dir, pubfile=pubfile))
    ftp.close()
    output_ok("common_secret.pem.pub file copied to {0}".format(slavehost))


def distribute_to_all_slave_nodes(ssh, pubfile):
    """
    Distribute the pem.pub file to all the slave nodes using
    Glusterd copy file infrastructure
    """
    stdin, stdout, stderr = ssh.exec_command(
        "gluster system:: copy file /geo-replication/{pubfile}".format(
            pubfile=pubfile))

    rc = stdout.channel.recv_exit_status()
    if rc == 0:
        output_ok("Master SSH Keys copied to all Up "
                  "Slave nodes")
    else:
        output_notok("Unable to copy Master SSH Keys to all Up "
                     "Slave nodes")


def add_to_authorized_keys(ssh, pubfile, slaveuser):
    """
    Add these pub keys to authorized_keys file of all Slave nodes
    """
    stdin, stdout, stderr = ssh.exec_command(
        "gluster system:: execute add_secret_pub {slaveuser} "
        "geo-replication/{pubfile}".format(
            pubfile=pubfile, slaveuser=slaveuser))

    rc = stdout.channel.recv_exit_status()
    if rc == 0:
        output_ok("Updated Master SSH Keys to all Up "
                  "Slave nodes authorized_keys file")
    else:
        output_notok("Unable to update Master SSH Keys to all "
                     "Up Slave nodes authorized_keys file")


def create_georep_session(args, slaveuser, slavehost, slavevol):
    """
    Create Geo-rep session using gluster volume geo-replication command
    """
    slave = slavehost
    if slaveuser != "root":
        slave = "{0}@{1}".format(slaveuser, slavehost)

    cmd = ["gluster", "volume", "geo-replication",
           args.mastervol,
           "{0}::{1}".format(slave, slavevol),
           "create",
           "no-verify"]

    cmd += ["force"] if args.force else []
    execute(cmd,
            success_msg="Geo-replication Session Established",
            failure_msg="Failed to Establish Geo-replication Session")


def setup_georep():
    """
    Main function to setup Geo-replication. Steps involved are
    1.  Collect root@SLAVEHOST's password
    2.  Check if SSH port is open
    3.  Initialize SSH Client
    4.  Compare the Gluster Versions
    5.  Compare disk sizes
    6.  Run gsec_create
    7.  Copy common_secret.pem.pub to Main Slave node
    8.  Distribute common_secret.pem.pub to all Slave nodes
    9.  Add to authorized_keys file
    10. Create Geo-replication Session
    """
    # Parse/Validate the CLI arguments
    args = get_args()

    if os.getuid() != 0:
        output_notok("Only root can run this tool!")

    # Modify the Global Config based on User input. If no coloring required
    global USE_CLI_COLOR
    if args.no_color:
        USE_CLI_COLOR = False

    # Collect Glusterd workdir, slave information
    georep_dir = os.path.join(get_glusterd_workdir(), "geo-replication")
    slavehost_data, slavevol = args.slave.split("::")
    slave = slavehost_data.split("@")
    slavehost = slave[-1]
    slaveuser = "root" if len(slave) == 1 else slave[0]

    # Get SLAVEHOST's root users password for administrative activities
    passwd_prompt_msg = ("Geo-replication session will be established "
                         "between {mastervol} and {slave}\n"
                         "Root password of {slavehost} is required to complete"
                         " the setup. NOTE: Password will not be stored.\n\n"
                         "root@{slavehost}'s password: ".format(
                             mastervol=args.mastervol,
                             slave=args.slave,
                             slavehost=slavehost))

    passwd = getpass.getpass(passwd_prompt_msg)

    # SSH Port check: Enabled/Disabled
    check_host_reachable(slavehost)

    # Initiate SSH Client
    ssh = ssh_initialize(slavehost, passwd)

    # Compare Gluster Version in Master Cluster and Slave Cluster
    compare_gluster_versions(ssh)

    # Compare disk size and used size to decide Master and Slave are compatible
    # Also check if Slave is empty or not
    compare_disk_sizes(args, slavehost, slavevol)

    # Run gsec_create command
    run_gsec_create(georep_dir)

    # Target name for Pubfile
    pubfile = "{mastervol}_{slavevol}_common_secret.pem.pub".format(
        mastervol=args.mastervol, slavevol=slavevol)

    # Copy Pub file to Main Slave node
    copy_to_main_slave_node(ssh, args, slavehost, georep_dir, pubfile)

    # Distribute SSH Keys to All the Slave nodes
    distribute_to_all_slave_nodes(ssh, pubfile)

    # Add the SSH Keys to authorized_keys file of all Slave nodes
    add_to_authorized_keys(ssh, pubfile, slaveuser)

    # Last Step: Create Geo-rep Session
    create_georep_session(args, slaveuser, slavehost, slavevol)


def get_args():
    """
    Parse the CLI arguments
    """
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=PROG_DESCRIPTION)

    parser.add_argument("mastervol", help="Master Volume Name",
                        metavar="MASTERVOL")
    parser.add_argument("slave",
                        help="Slave, HOSTNAME or root@HOSTNAME::SLAVEVOL "
                        "or user@HOSTNAME::SLAVEVOL",
                        metavar="SLAVE")
    parser.add_argument("--force", help="Force",
                        action="store_true")
    parser.add_argument("--no-color", help="No Terminal Colors",
                        action="store_true")

    return parser.parse_args()


def main():
    """
    Main function to handle Keyboard inturrupt.
    """
    try:
        setup_georep()
    except KeyboardInterrupt:
        sys.stderr.write("\nExiting..\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
