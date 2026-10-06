#!/bin/sh
#
# Generate the man page of ipmitool.py from its argparse definition.
#
# Needs argparse-manpage (pip install argparse-manpage). The date in the
# man page header can be set with SOURCE_DATE_EPOCH.

set -e

cd "$(dirname "$0")/.."

PYTHONPATH=. argparse-manpage \
	--pyfile man/build_parser.py \
	--function build_parser \
	--prog ipmitool.py \
	--project-name python-ipmi \
	--description "pure python IPMI tool" \
	--manual-title "python-ipmi manual" \
	--url https://github.com/kontron/python-ipmi \
	--include man/ipmitool.py.1.include \
	--output man/ipmitool.py.1
