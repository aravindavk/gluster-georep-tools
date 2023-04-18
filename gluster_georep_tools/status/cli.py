# Doc shown in CLI Help
"""
Gluster Geo-replication Status
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import sys

from glustercli.cli import georep
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
        print("SESSION: " + session[0])
        table = PrettyTable([
            "PRIMARY", "STATUS",
            "CRAWL STATUS", "SECONDARY NODE", "LAST SYNCED"
        ])
        for row in session[2]:
            table.add_row([
                row["master_node"] + ":" + row["master_brick"],
                row["status"], row["crawl_status"],
                row["slave_node"], row["last_synced"]
            ])

        # If Table has data
        if session[2]:
            print(table)
        else:
            # When no filters match
            print("-")

        print("Active: {active} | Passive: {passive} | "
               "Faulty: {faulty} | Created: {created} | "
               "Offline: {offline} | Stopped: {stopped} | "
               "Initializing: {initializing} | "
               "Total: {total}".format(**session[1]))

        # Empty line in output
        print()


def handle_status(args):
    secondary_user = "root"
    secondary_host = None
    secondary_vol = None
    volname = None

    if args.primary_vol is not None:
        volname = args.primary_vol

    if args.secondary is not None:
        if "::" not in args.secondary:
            sys.stderr.write("Invalid Secondary details\n")
            sys.exit(1)

        secondary_host_tmp, secondary_vol = args.secondary.split("::")

        secondary_host_data = secondary_host_tmp.split("@")
        secondary_host = secondary_host_data[-1]
        if len(secondary_host_data) > 1:
            secondary_user = secondary_host_data[0]

    status_data = georep.status(volname=volname,
                                slave_host=secondary_host,
                                slave_vol=secondary_vol,
                                slave_user=secondary_user)

    if not status_data:
        if args.secondary is not None:
            sys.stderr.write("No active Geo-replication "
                             "sessions between {0} and {1}\n".format(
                                 args.primary_vol,
                                 args.secondary))
            sys.exit(1)
        elif args.primary_vol is not None and args.secondary is None:
            sys.stderr.write("No active Geo-replication "
                             "sessions for {0}\n".format(
                                 args.primary_vol))
            sys.exit(1)

    status_data = apply_filters(status_data, args)
    display_status(status_data)


def get_args():
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)
    parser.add_argument("primary_vol", nargs="?", help="Primary Volume Name")
    parser.add_argument("secondary", nargs="?", help="Secondary details. "
                        "<secondary_host>::<secondary_vol>, "
                        "Example: secondary_node1::myvol")
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
