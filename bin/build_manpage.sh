#!/bin/sh
#
# Generate the man page of pyipmi from its argparse definition.
#
# Needs argparse-manpage (pip install argparse-manpage). The date in the
# man page header can be set with SOURCE_DATE_EPOCH.

set -e

cd "$(dirname "$0")/.."

PYTHONPATH=. argparse-manpage \
	--pyfile man/build_parser.py \
	--function build_parser \
	--prog pyipmi \
	--project-name python-ipmi \
	--description "pure python IPMI tool" \
	--manual-title "python-ipmi manual" \
	--url https://github.com/kontron/python-ipmi \
	--include man/pyipmi.1.include \
	--output man/pyipmi.1
