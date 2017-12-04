#!/bin/bash
#
# A command-line script for running the cli if
# you haven't installed it using pip. Mainly
# useful for developers, I think.


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd ${DIR}
pipenv run -- python -m sucks.cli "$@"
