#!/usr/bin/env bash

set -o pipefail nounset errexit

function setup () {
    cd output && docker compose up || true
    docker compose down
}

python3 iperf-traffic-generator.py && setup
