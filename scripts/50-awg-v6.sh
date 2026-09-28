#!/bin/sh
# ndm rebuilds policy tables on interface events, sometimes after this hook fires;
# re-apply the IPv6 reject a few times in the background.
echo "$(date '+%T') $id $system_name $layer $level" >> /opt/var/log/awg-fi-hook.log
( for s in 1 3 5 10; do sleep $s; /opt/sbin/awg-v6block; done ) </dev/null >/dev/null 2>&1 &
