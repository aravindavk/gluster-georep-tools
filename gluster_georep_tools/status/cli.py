# Doc shown in CLI Help
"""
Gluster Geo-replication Status
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import sys

from gluster.cli import georep
from prettytable import PrettyTable


def apply_filters(status_data, args):
    session_rows = []
    for session in status_data:
        # Collect the Session name and apply filter
        # Session name will be present even though filters don't match
        session_name = "{0} ==> {1}".format(
            session[0]["mastervol"],
            session[0]["slave"].replace("ssh://", ""))
        session_rows.append([session_name, {}, []])

        summary = {
            "active": 0,
            "passive": 0,
            "created": 0,
            "stopped": 0,
            "offline": 0,
            "initializing": 0,
            "faulty": 0,
            "total": len(session)
        }

        # Apply all filters, do not add if filter not satisfied
        for row in session:
            summary[row["status"].replace("...", "").lower()] += 1

            # --with-status filter
            if args.with_status is not None and \
               args.with_status.lower() not in row["status"].lower():
                continue

            # --with-crawl-status filter
            if args.with_crawl_status is not None and \
               args.with_crawl_status.lower() not in \
               row["crawl_status"].lower():
                continue

            # Add to final output
            session_rows[-1][2].append(row)

        session_rows[-1][1] = summary.copy()

    return session_rows


def display_status(status_data):
    for session in status_data:
        # Display heading and initiate table
        print "SESSION: " + session[0]
        table = PrettyTable(["MASTER", "STATUS",
                             "CRAWL STATUS", "SLAVE NODE", "LAST SYNCED",
                             "CHKPT TIME", "CHKPT COMPLETED",
                             "CHKPT COMPLETION TIME"])
        for row in session[2]:
            table.add_row([row["master_node"] + ":" + row["master_brick"],
                           row["status"], row["crawl_status"],
                           row["slave_node"], row["last_synced"],
                           row["checkpoint_time"],
                           row["checkpoint_completed"],
                           row["checkpoint_completion_time"]])

        # If Table has data
        if session[2]:
            print table
        else:
            # When no filters match
            print "-"

        print ("Active: {active} | Passive: {passive} | "
               "Faulty: {faulty} | Created: {created} | "
               "Offline: {offline} | Stopped: {stopped} | "
               "Initializing: {initializing} | "
               "Total: {total}".format(**session[1]))

        # Empty line in output
        print


def handle_status(args):
    slave_user = "root"
    slave_host = None
    slave_vol = None
    volname = None

    if args.mastervol is not None:
        volname = args.mastervol

    if args.slave is not None:
        if "::" not in args.slave:
            sys.stderr.write("Invalid Slave details\n")
            sys.exit(1)

        slave_host_tmp, slave_vol = args.slave.split("::")

        slave_host_data = slave_host_tmp.split("@")
        slave_host = slave_host_data[-1]
        if len(slave_host_data) > 1:
            slave_user = slave_host_data[0]

    status_data = georep.status(volname=volname,
                                slave_host=slave_host,
                                slave_vol=slave_vol,
                                slave_user=slave_user)

    if not status_data:
        if args.slave is not None:
            sys.stderr.write("No active Geo-replication "
                             "sessions between {0} and {1}\n".format(
                                 args.mastervol,
                                 args.slave))
            sys.exit(1)
        elif args.mastervol is not None and args.slave is None:
            sys.stderr.write("No active Geo-replication "
                             "sessions for {0}\n".format(
                                 args.mastervol))
            sys.exit(1)

    status_data = apply_filters(status_data, args)
    display_status(status_data)


def get_args():
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)
    parser.add_argument("mastervol", nargs="?", help="Master Volume Name")
    parser.add_argument("slave", nargs="?", help="Slave details. "
                        "[<slave_user>@]<slave_host>::<slave_vol>, "
                        "Example: geoaccount@slavenode1::myvol or "
                        "slavenode1::myvol in case of root user")
    parser.add_argument("--with-status",
                        help="Show only nodes with matching Status")
    parser.add_argument("--with-crawl-status",
                        help="Show only nodes with matching Crawl Status")
    return parser.parse_args()


def main():
    args = get_args()
    handle_status(args)


if __name__ == "__main__":
    main()
