#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter, Service
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
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
        # choices=[Platform.AMD64, Platform.ARM64],
        choices=list(Platform),
        type=Platform,
        default=Platform.AMD64,
        help="Specify the platform: amd or arm (default: amd)",
    )

    # NOTE: expected behavior: something like `docker run -v $HOME/dump:/root/iperf-generator.log`",
    # See the docs: https://docs.docker.com/engine/storage/volumes/#use-a-volume-with-docker-compose
    # Case 1: The user doesn't specify the -v flag - no volume should be made / written to
    # Case 2: User specifies the -v with nothing - I should log to a default location, defined within my program.
    # Case 3: User specifies -v and a string(path) - I should log to the given path

    # TODO: using w/o -v will have host dir be None, but container dir be /logs/

    parser.add_argument(
        "-v",
        "--volume",
        type=str,
        nargs='?', # means 0-or-1 arguments
        const="/home/josh/research-projects/iperf3-logs/ip.log", # sets the default when there are 0 arguments (-v)
        default=None, # if no -v given at all, does nothing
        help="Name of volume — syntax is `-v <optional_path>`",
        # required=True,
        # action="store", # redundant, default
    )
    return parser.parse_args()

def createServiceList(count: int) -> list[Service]:
    """
    Create a list of Service instances.

    @param count: The number of Service instances to create.
    """
    return [Service() for _ in range(count)]


def expand_network(base, emu, start_asn=200, num_as=10, hosts_per_as=25):
    """
    Expand the network by adding new Autonomous Systems (ASes) and hosts.

    @param base: The base layer of the emulator.
    @param emu: The emulator instance.
    @param start_asn: The starting ASN for the new ASes.
    @param num_as: The number of ASes to add.
    @param hosts_per_as: The number of hosts to create in each AS.
    """
    for i in range(num_as):
        asn = start_asn + i
        # Cycle through exchanges 100-105
        exchange = 100 + (i % 6)
        # Use custom prefix for ASNs > 255, as those execeeding 255
        # can't get the default network prefix assignment
        # default: `10.{asn}.{id}.0/24`, see ../../../../docs/user_manual/as.md
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

        print(f"Created ASN {asn} with {hosts_per_as} hosts, connected to IX{exchange}")

def run(dumpfile=None):
    ###############################################################################
    # Get args from cmdline
    args = parse_args()

    emu = Emulator()

    # Run the pre-built components
    mini_internet.run(dumpfile='./base_internet.bin')
    
    # Load and merge the pre-built components 
    emu.load('./base_internet.bin')
    
    base = emu.getLayer("Base")

    etc_hosts = EtcHosts()


    traffic_service = TrafficService()

    traffic_service.install("iperf-receiver-1", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install("iperf-receiver-2", TrafficServiceType.IPERF_RECEIVER, log_file="/root/iperf3_receiver.log")
    traffic_service.install(
        "iperf-generator",
        TrafficServiceType.IPERF_GENERATOR,
        log_file="/root/iperf3_generator.log",
        protocol="TCP",
        duration=30,
        # bits/sec (0 for unlimited)
        rate=0,
        extra_options="",
        # --bidir -b 0
        # "-b 0" will disable bandwidth limit
    ).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])

    ### Original
    # # Add hosts to AS-150
    # as150 = base.getAutonomousSystem(150)
    # as150.createHost("iperf-generator").joinNetwork("net0")
    # # Add hosts to AS-162
    # as162 = base.getAutonomousSystem(162)
    # as162.createHost("iperf-receiver-1").joinNetwork("net0")
    # 
    # # Add hosts to AS-171
    # as171 = base.getAutonomousSystem(171)
    # as171.createHost("iperf-receiver-2").joinNetwork("net0")
    # 
    # # Binding virtual nodes to physical nodes
    # emu.addBinding(
    #     Binding("iperf-generator", filter=Filter(asn=150, nodeName="iperf-generator"))
    # )
    # emu.addBinding(
    #     Binding("iperf-receiver-1", filter=Filter(asn=162, nodeName="iperf-receiver-1"))
    # )
    # emu.addBinding(
    #     Binding("iperf-receiver-2", filter=Filter(asn=171, nodeName="iperf-receiver-2"))
    # )

    ########

    # Expand the network
    # expand_network(base, emu)
    expand_network(base, emu, start_asn=200, num_as=args.as_count, hosts_per_as=args.num_hosts)

    # Add hosts to AS-200
    as200 = base.getAutonomousSystem(200)
    as200.createHost("iperf-generator").joinNetwork("net0")

    # Add hosts to AS-201
    as201 = base.getAutonomousSystem(201)
    as201.createHost("iperf-receiver-1").joinNetwork("net0")

    # Add hosts to AS-202
    as201 = base.getAutonomousSystem(202)
    as201.createHost("iperf-receiver-2").joinNetwork("net0")

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

    gen = as200.getHost("iperf-generator")
    # # https://stackoverflow.com/questions/30487767/check-if-argparse-optional-argument-is-set-or-not
    # container_logdir: str = "/root"
    # if args.volume is not None:
    #     host_logdir: str = args.volume
    #     gen = as150.getHost("iperf-generator")
    #     gen.addSharedFolder(container_logdir, host_log)
    # else:
    #     gen = as150.getHost("iperf-generator")
    #     gen.addSharedFolder(container_logdir, "/home/josh/research-projects/iperf3-logs")

    # Using a FILE
    # This is what it is in ../../../../seedemu/services/TrafficService/traffic_generator.py
    # container_logdir: str = "/root/traffic_generator.log"
    # host_logdir: str = args.volume

    # Using a DIR
    container_logdir: str = "/logs"
    host_logdir: str = "/home/josh/research-projects/iperf3-logs"

    # ADD BIND MOUNT
    gen.addSharedFolder(container_logdir, host_logdir)

    # gen.addBuildCommand()

    # ADD SHARED VOLUME
    # vol_name_host: str = "test"
    # gen.addPersistentStorage(f"{vol_name_host}:{container_logdir}")


    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(etc_hosts)

    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       emu.compile(Docker(platform=args.platform), './output', override=True)
       # emu.compile(Docker(platform=Platform.AMD64), './output', override=True)

if __name__ == "__main__":
    run()
