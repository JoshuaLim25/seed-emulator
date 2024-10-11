# Current container scripts

`./start.sh` for `TrafficGenerator(Server)`

```sh
mkdir -p /logs
echo "Check if targets are reachable";
while read client; do
    while true; do ping -c1 $client > /dev/null && break; done;
done < /root/traffic-targets
echo "Starting traffic generator"
while read client; do
    iperf3 -c $client --logfile /root/iperf3_generator.log -t 30 -b 0  &
done < /root/traffic-targets
```

---

`root/traffic_generator_iperf3.sh`

```sh
#!/bin/bash
cat /tmp/etc-hosts >> /etc/hosts
chmod +x /interface_setup
/interface_setup
ip rou del default 2> /dev/null
ip route add default via 10.200.0.254 dev net0
chmod +x /root/traffic_generator_iperf3.sh
/root/traffic_generator_iperf3.sh &

echo "ready! run 'docker exec -it $HOSTNAME /bin/zsh' to attach to this node" >&2
for f in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > "$f"; done
tail -f /dev/null
```


# tail or watch

### `tail -f -n0` 

**Pros:**
- **Real-time monitoring:** `tail -f` will show new lines as they are added to the file in real-time, making it great for live logs.
- **Minimal overhead:** It continuously reads the file without periodic polling, which is often more efficient.
- **Focus on content:** It only displays the new entries, allowing you to concentrate on what's relevant.

**Cons:**
- **Limited filtering:** `tail` doesn't natively filter for specific content. You’d need to pipe it through `grep` to show only lines containing "Done.", e.g., `tail -f logfile | grep "Done."`.
- **Less control over display:** You can’t easily modify how often it checks or displays the data.

### `watch`

**Pros:**
- **Flexible command execution:** You can run any command, which could be tailored to show just the line you want (e.g., `watch "grep 'Done.' logfile"`).
- **Regular intervals:** You can set the refresh interval, which can be useful for reducing output clutter if you're expecting a lot of log entries.
- **Clear display:** It clears the screen before each update, which can help focus on the most recent output.

**Cons:**
- **Polling overhead:** It runs the specified command at set intervals, which can lead to delays in seeing new entries.
- **May miss rapid updates:** If "Done." appears between checks, you might miss it if you're not looking at the terminal during that interval.

### Conclusion

For your specific case of waiting for a line containing "Done." to appear, `tail -f -n0` with `grep` would generally be the better choice because it provides real-time feedback and is more efficient for watching logs. You can use:

```bash
tail -f logfile | grep "Done."
```

This way, you’ll see the relevant lines as they appear without missing anything. If you find yourself needing more context or control over how often you check, consider using `watch`, but for immediate updates, `tail` is typically preferred.

