#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter, Service
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
from examples.internet.B00_mini_internet import mini_internet
from seedemu.utilities import Makers
import os, sys

def createServiceList(count: int) -> list[Service]:
    """
    Create a list of Service instances.

    @param count: The number of Service instances to create.
    """
    return [Service() for _ in range(count)]

def expand_network(emu: Emulator, base: Base, ebgp: Ebgp, start_asn=200, num_as=10, hosts_per_as=3):
    """
    Expand the network by adding new Autonomous Systems (ASes) and hosts.

    @param emu: The emulator instance.
    @param base: The base layer of the emulator.
    @param ebgp: The EBGP layer of the emulator.
    @param start_asn: The starting ASN for the new ASes.
    @param num_as: The number of ASes to add.
    @param hosts_per_as: The number of hosts to create in each AS.
    """
    for i in range(num_as):
        asn = start_asn + i
        # Cycle through exchanges 100-104
        exchange = 100 + (i % 5)
        
        # Use custom prefix for ASNs >= 256
        if asn >= 256:
            prefix = f'10.{asn // 256}.{asn % 256}.0/24'
            stub_as = base.createAutonomousSystem(asn)
            stub_as.createNetwork('net0', prefix=prefix)
            router = stub_as.createRouter('router0')
            router.joinNetwork('net0')
            router.joinNetwork(f'ix{exchange}')
            
            for j in range(hosts_per_as):
                name = f'host_{j}'
                host = stub_as.createHost(name)
                host.joinNetwork('net0')
        else:
            Makers.makeStubAsWithHosts(emu, base, asn, exchange, hosts_per_as)
        
        # Add peering relationship
        transit_as = 2 + (i % 3)  # Cycle through transit ASes 2, 3, 4
        ebgp.addPrivatePeerings(exchange, [transit_as], [asn], PeerRelationship.Provider)
        
        print(f"Created ASN {asn} with {hosts_per_as} hosts, connected to IX{exchange}, peering with AS{transit_as}")


def run(dumpfile=None):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)

    emu = Emulator()

    # Run the pre-built components
    mini_internet.run(dumpfile='./base_internet.bin')

    # Load and merge the pre-built components 
    emu.load('./base_internet.bin')

    base = emu.getLayer("Base")
    ebgp = emu.getLayer("Ebgp")

    etc_hosts = EtcHosts()

    traffic_service = TrafficService()
    traffic_service.install("iperf-receiver-1", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install("iperf-receiver-2", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install(
        "iperf-generator",
        TrafficServiceType.IPERF_GENERATOR,
        log_file="/root/iperf3_generator.log",
        protocol="TCP",
        duration=90,
        # bits/sec (0 for unlimited)
        rate=0,
        extra_options="--bidir",
        # "-b 0" will disable bandwidth limit
    ).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])

    # Add hosts to AS-150
    as150 = base.getAutonomousSystem(150)
    as150.createHost("iperf-generator").joinNetwork("net0")

    # Add hosts to AS-162
    as162 = base.getAutonomousSystem(162)
    as162.createHost("iperf-receiver-1").joinNetwork("net0")

    # Add hosts to AS-171
    as171 = base.getAutonomousSystem(171)
    as171.createHost("iperf-receiver-2").joinNetwork("net0")

    # Binding virtual nodes to physical nodes
    emu.addBinding(
        Binding("iperf-generator", filter=Filter(asn=150, nodeName="iperf-generator"))
    )
    emu.addBinding(
        Binding("iperf-receiver-1", filter=Filter(asn=162, nodeName="iperf-receiver-1"))
    )
    emu.addBinding(
        Binding("iperf-receiver-2", filter=Filter(asn=171, nodeName="iperf-receiver-2"))
    )

    # Expand the network
    expand_network(emu, base, ebgp, start_asn=200, num_as=20, hosts_per_as=2)

    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(etc_hosts)

    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       emu.compile(Docker(platform=platform), './output', override=True)

if __name__ == "__main__":
    run()
