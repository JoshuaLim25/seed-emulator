#!/bin/sh

# Exit on error, unset var, pipe fail
set -o pipefail nounset errexit

setup () {
    cd output && docker compose build && docker compose up
}

python3 multi-traffic-generator.py && setup
