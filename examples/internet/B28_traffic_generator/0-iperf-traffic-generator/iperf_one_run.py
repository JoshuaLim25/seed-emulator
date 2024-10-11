#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter, Service
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts, Ebgp, PeerRelationship
from examples.internet.B00_mini_internet import mini_internet
from seedemu.utilities import Makers
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Run the SEED emulator with specified network size (number of nodes, ASes, etc).")
    parser.add_argument(
        "-n",
        "--num_hosts",
        type=int,
        help="Number of hosts assigned to each new autonomous system",
        required=True,
        action="store"
    )
    parser.add_argument(
        "-a",
        "--as_count",
        type=int,
        help="Number of new Autonomous Systems to create",
        required=True,
        action="store"
    )
    parser.add_argument(
        "--platform",
        choices=list(Platform),
        type=Platform,
        default=Platform.AMD64,
        help="Specify the platform: amd or arm (default: amd)",
    )
    parser.add_argument(
        "-v",
        "--volume",
        type=str,
        nargs='?',
        const="/home/josh/research-projects/iperf3-logs/iperf3_generator.log",
        default=None,
        help="Name of volume — syntax is `-v <optional_path>`",
    )
    return parser.parse_args()

def expand_network(base, emu, ebgp, start_asn=200, num_as=5, hosts_per_as=5):
    """
    Expand the network by adding new Autonomous Systems (ASes) and hosts.
    Sets up proper BGP peering and transit relationships.
    Each new AS peers with the route server at its exchange
    Each new AS establishes transit relationships with available Tier 1 providers
    """
    # List to keep track of all new ASNs for peering setup
    new_asns = []
    
    # Dictionary to map exchanges to their connected ASNs
    ix_to_asns = {
        100: [], 101: [], 102: [], 103: [], 104: [], 105: []
    }

    for i in range(num_as):
        asn = start_asn + i
        # Cycle through exchanges 100-105
        exchange = 100 + (i % 6)
        
        # Keep track of which ASNs are connected to which exchange
        ix_to_asns[exchange].append(asn)
        new_asns.append(asn)

        if asn >= 256:
            prefix = f'10.{asn // 256}.{asn % 256}.0/24'
            stub_as = base.createAutonomousSystem(asn)
            stub_as.createNetwork('net0', prefix=prefix)
            router = stub_as.createRouter('router0')
            router.joinNetwork('net0')
            router.joinNetwork(f'ix{exchange}')
            stub_as.joinNetwork(f'ix{exchange}')

            for j in range(hosts_per_as):
                name = f'host_{j}'
                host = stub_as.createHost(name)
                host.joinNetwork('net0')
        else:
            Makers.makeStubAsWithHosts(emu, base, asn, exchange, hosts_per_as)

    # Set up BGP peering relationships for all new ASes
    for exchange, asns in ix_to_asns.items():
        if asns:  # Only process exchanges that have new ASes
            # 1. Peer with the route server
            ebgp.addRsPeers(exchange, asns)
            
            # 2. Set up transit relationships with Tier 1 providers
            tier1_providers = {
                100: [2, 3, 4],    # NYC
                101: [2],          # San Jose
                102: [2, 4],       # Chicago
                103: [3],          # Miami
                104: [3, 4],       # Boston
                105: [2, 3]        # Houston
            }
            
            for asn in asns:
                # Connect to all available Tier 1 providers at this exchange
                for provider in tier1_providers[exchange]:
                    ebgp.addPrivatePeerings(
                        exchange, [provider], [asn], 
                        PeerRelationship.Provider
                    )

    return new_asns

def run(dumpfile=None):
    args = parse_args()
    emu = Emulator()
    
    # Run the pre-built components
    mini_internet.run(dumpfile='./base_internet.bin')
    
    # Load and merge the pre-built components 
    emu.load('./base_internet.bin')
    
    ebgp = emu.getLayer("Ebgp")
    base = emu.getLayer("Base")
    etc_hosts = EtcHosts()

    traffic_service = TrafficService()

    # Set up traffic service
    traffic_service.install("iperf-receiver-1", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install("iperf-receiver-2", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install(
        "iperf-generator",
        TrafficServiceType.IPERF_GENERATOR,
        log_file="/root/iperf3_generator.log",
        protocol="TCP",
        duration=30,
        rate=0,
        extra_options=""
    ).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])

    # Expand the network (and get the list of new ASNs)
    new_asns = expand_network(base, emu, ebgp, start_asn=200, num_as=args.as_count, hosts_per_as=args.num_hosts)

    # Add hosts to the first three new ASes
    as200 = base.getAutonomousSystem(200)
    as200.createHost("iperf-generator").joinNetwork("net0")

    as201 = base.getAutonomousSystem(201)
    as201.createHost("iperf-receiver-1").joinNetwork("net0")

    as202 = base.getAutonomousSystem(202)
    as202.createHost("iperf-receiver-2").joinNetwork("net0")

    # Binding virtual nodes to physical nodes
    emu.addBinding(
        Binding("iperf-generator", filter=Filter(asn=200, nodeName="iperf-generator"))
    )
    emu.addBinding(
        Binding("iperf-receiver-1", filter=Filter(asn=201, nodeName="iperf-receiver-1"))
    )
    emu.addBinding(
        Binding("iperf-receiver-2", filter=Filter(asn=202, nodeName="iperf-receiver-2"))
    )

    # Add the bind mount
    gen = as200.getHost("iperf-generator")
    host_logdir = args.volume
    container_logdir = "/root/iperf3_generator.log"
    gen.addSharedFolder(container_logdir, host_logdir)


    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(etc_hosts)

    if dumpfile is not None:
       emu.dump(dumpfile)
    else:
       emu.render()
       emu.compile(Docker(platform=args.platform), './output', override=True)

if __name__ == "__main__":
    run()
