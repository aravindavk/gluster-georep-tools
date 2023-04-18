# -*- coding: utf-8 -*-

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
Primary Gluster Volume to Secondary Gluster Volume.
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
                   "in Secondary Volume")


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
    p = subprocess.Popen(cmd, universal_newlines=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
                         universal_newlines=True,
                         stdout=subprocess.PIPE)

    out, _ = p.communicate()

    if p.returncode == 0:
        return out.strip()
    else:
        return DEFAULT_GLUSTERD_WORKDIR


def check_host_reachable(secondary_host):
    """
    Check if SSH port is open for given secondary_host
    """
    if is_port_enabled(secondary_host, 22):
        output_ok("{0} is Reachable(Port 22)".format(secondary_host))
    else:
        output_notok("{0} is Not Reachable(Port 22)".format(secondary_host))


def ssh_initialize(secondary_host, username, passwd):
    """
    Initialize the SSH connection
    """
    ssh = paramiko.SSHClient()
    try:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(secondary_host, username=username, password=passwd)
        output_ok("SSH Connection established {0}@{1}".format(username, secondary_host))
    except paramiko.ssh_exception.AuthenticationException as e:
        output_notok("Unable to establish SSH connection "
                     "to {0}@{1}:\n{2}".format(username, secondary_host, e))

    return ssh


def compare_gluster_versions(ssh):
    """
    Collect Primary version by directly executing CLI command, get
    Secondary version via SSH command execution
    """
    # Collect Gluster Version from Primary
    primary_version = execute(["gluster", "--version"],
                              failure_msg="Failed to get Gluster version "
                              "from Primary Cluster")
    primary_version = primary_version.split()[1]

    sudo_pfx = "sudo " if ssh.use_sudo else ""

    # Collect Gluster Version from Secondary
    stdin, stdout, stderr = ssh.exec_command(f"{sudo_pfx} gluster --version")
    rc = stdout.channel.recv_exit_status()
    if rc != 0:
        output_notok("Unable to get Secondary Gluster Version")

    secondary_version = stdout.readline().split()[1]

    # Check for Version mismatch
    if primary_version == secondary_version:
        output_ok("Primary Volume and Secondary Volume are "
                  "compatible (Version: {0})".format(primary_version))
    else:
        output_notok("Primary Volume({0}) and Secondary Volume({1}) "
                     "versions not Compatible".format(primary_version,
                                                      secondary_version))


def compare_disk_sizes(args, secondary_host, secondary_vol):
    """
    Compare the disk sizes and available sizes. Also
    Check Secondary volume is empty or not
    """
    primary_disk_size = None
    secondary_disk_size = None
    primary_used_size = None
    secondary_used_size = None

    with glustermount("localhost", args.primary_vol) as mnt:
        data = os.statvfs(mnt)
        primary_disk_size = data.f_blocks * data.f_bsize
        primary_used_size = ((data.f_blocks - data.f_bavail) *
                            data.f_bsize)

    with glustermount(secondary_host, secondary_vol) as mnt:
        if get_number_of_files(mnt):
            if not args.force:
                cleanup(secondary_host, secondary_vol, mnt)
                output_notok("{0}::{1} is not empty. Please delete existing "
                             "files in {0}::{1} and retry, or use --force to "
                             "continue without deleting the existing "
                             "files.".format(secondary_host, secondary_vol))
            else:
                output_warning("{0}::{1} is not empty.".format(secondary_host,
                                                               secondary_vol))
        data = os.statvfs(mnt)
        secondary_disk_size = data.f_blocks * data.f_bsize
        secondary_used_size = ((data.f_blocks - data.f_bavail) *
                            data.f_bsize)

    if primary_disk_size is None or primary_used_size is None:
        msg = "Unable to get Disk size and Used size of Primary Volume"
        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)

    if secondary_disk_size is None or secondary_used_size is None:
        msg = "Unable to get Disk size and Used size of Secondary Volume"
        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)

    if secondary_disk_size < primary_disk_size:
        msg = ("Total disk size of primary({0}) is greater "
               "than disk size of secondary({1})".format(
                   human_readable_size(primary_disk_size),
                   human_readable_size(secondary_disk_size)))
        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)

    effective_primary_used_size = primary_used_size + BUFFER_SIZE
    secondary_available_size = secondary_disk_size - secondary_used_size
    primary_available_size = primary_disk_size - effective_primary_used_size

    if secondary_available_size < primary_available_size:
        msg = ("Total available size of primary({0}) is greater "
               "than available size of secondary({1})".format(
                   human_readable_size(primary_available_size),
                   human_readable_size(secondary_available_size)))

        if not args.force:
            output_notok(msg)
        else:
            output_warning(msg)


def run_gsec_create(georep_dir):
    """
    gsec_create command to generate pem keys in all the primary nodes
    and collect all pub keys to single node
    """
    execute(["gluster", "system::", "execute", "gsec_create"],
            success_msg="Common secret pub file present at "
            "{0}/common_secret.pem.pub".format(georep_dir),
            failure_msg="Common secret pub file generation failed")


def copy_to_main_secondary_node(ssh, args, secondary_host, georep_dir, pubfile):
    """
    Copy common_secret.pem.pub file to Main Secondary node
    """
    home_dir = "/root"
    if args.secondary_user != "root":
        home_dir = f"/home/{args.secondary_user}"

    # Copy common_secret.pem.pub file to Main Secondary node
    ftp = ssh.open_sftp()
    ftp.put(
        f"{georep_dir}/common_secret.pem.pub",
        f"{home_dir}/{pubfile}"
    )
    ftp.close()

    sudo_pfx = "sudo " if ssh.use_sudo else ""
    stdin, stdout, stderr = ssh.exec_command(
        f"{sudo_pfx}cp {home_dir}/{pubfile} {georep_dir}/{pubfile}")

    output_ok("common_secret.pem.pub file copied to {0}".format(secondary_host))


def distribute_to_all_secondary_nodes(ssh, pubfile):
    """
    Distribute the pem.pub file to all the secondary nodes using
    Glusterd copy file infrastructure
    """
    sudo_pfx = "sudo " if ssh.use_sudo else ""
    stdin, stdout, stderr = ssh.exec_command(
        f"{sudo_pfx}gluster system:: copy file /geo-replication/{pubfile}")

    rc = stdout.channel.recv_exit_status()
    if rc == 0:
        output_ok("Primary SSH Keys copied to all Up "
                  "Secondary nodes")
    else:
        output_notok("Unable to copy Primary SSH Keys to all Up "
                     "Secondary nodes")


def add_to_authorized_keys(ssh, pubfile, secondary_session_user):
    """
    Add these pub keys to authorized_keys file of all Secondary nodes
    """
    sudo_pfx = "sudo " if ssh.use_sudo else ""
    stdin, stdout, stderr = ssh.exec_command(
        f"{sudo_pfx}gluster system:: execute add_secret_pub {secondary_session_user} "
        f"geo-replication/{pubfile}"
    )

    rc = stdout.channel.recv_exit_status()
    if rc == 0:
        output_ok("Updated Primary SSH Keys to all Up "
                  "Secondary nodes authorized_keys file")
    else:
        output_notok("Unable to update Primary SSH Keys to all "
                     "Up Secondary nodes authorized_keys file")


def create_georep_session(args, secondary_session_user, secondary_host, secondary_vol):
    """
    Create Geo-rep session using gluster volume geo-replication command
    """
    secondary = secondary_host
    if secondary_session_user != "root":
        secondary = "{0}@{1}".format(secondary_session_user, secondary_host)

    cmd = ["gluster", "volume", "geo-replication",
           args.primary_vol,
           "{0}::{1}".format(secondary, secondary_vol),
           "create",
           "no-verify"]

    cmd += ["force"] if args.force else []
    execute(cmd,
            success_msg="Geo-replication Session Established",
            failure_msg="Failed to Establish Geo-replication Session")


def setup_georep():
    """
    Main function to setup Geo-replication. Steps involved are
    1.  Collect root@SECONDARY_HOST's password
    2.  Check if SSH port is open
    3.  Initialize SSH Client
    4.  Compare the Gluster Versions
    5.  Compare disk sizes
    6.  Run gsec_create
    7.  Copy common_secret.pem.pub to Main Secondary node
    8.  Distribute common_secret.pem.pub to all Secondary nodes
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

    # Collect Glusterd workdir, secondary information
    georep_dir = os.path.join(get_glusterd_workdir(), "geo-replication")
    secondary_host_data, secondary_vol = args.secondary.split("::")
    secondary = secondary_host_data.split("@")
    secondary_host = secondary[-1]
    secondary_session_user = "root" if len(secondary) == 1 else secondary[0]

    # Get SECONDARY_HOST's root users password for administrative activities
    passwd_prompt_msg = (f"Geo-replication session will be established "
                         f"between {args.primary_vol} and {args.secondary}\n"
                         f"{args.secondary_user}@{secondary_host} password is "
                         f"required to complete"
                         f" the setup. NOTE: Password will not be stored.\n\n"
                         f"{args.secondary_user}@{secondary_host}'s password: ")

    passwd = getpass.getpass(passwd_prompt_msg)

    # SSH Port check: Enabled/Disabled
    check_host_reachable(secondary_host)

    # Initiate SSH Client
    ssh = ssh_initialize(secondary_host, args.secondary_user, passwd)

    # Use sudo while running commands in secondary node
    ssh.use_sudo = args.secondary_user != "root"

    # Compare Gluster Version in Primary Cluster and Secondary Cluster
    compare_gluster_versions(ssh)

    # Compare disk size and used size to decide
    # Primary and Secondary are compatible
    # Also check if Secondary is empty or not
    compare_disk_sizes(args, secondary_host, secondary_vol)

    # Run gsec_create command
    run_gsec_create(georep_dir)

    # Target name for Pubfile
    pubfile = "{primary_vol}_{secondary_vol}_common_secret.pem.pub".format(
        primary_vol=args.primary_vol, secondary_vol=secondary_vol)

    # Copy Pub file to Main Secondary node
    copy_to_main_secondary_node(ssh, args, secondary_host, georep_dir, pubfile)

    # Distribute SSH Keys to All the Secondary nodes
    distribute_to_all_secondary_nodes(ssh, pubfile)

    # Add the SSH Keys to authorized_keys file of all Secondary nodes
    add_to_authorized_keys(ssh, pubfile, secondary_session_user)

    # Last Step: Create Geo-rep Session
    create_georep_session(args, secondary_session_user, secondary_host, secondary_vol)


def get_args():
    """
    Parse the CLI arguments
    """
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=PROG_DESCRIPTION)

    parser.add_argument("primary_vol", help="Primary Volume Name",
                        metavar="PRIMARY_VOL")
    parser.add_argument("secondary",
                        help="Secondary, HOSTNAME or "
                        "HOSTNAME::SECONDARY_VOL",
                        metavar="SECONDARY")
    parser.add_argument(
        "--secondary-user", default="root",
        help="Admin user in one of the node of the secondary cluster"
    )
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
