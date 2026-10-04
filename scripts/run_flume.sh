#!/usr/bin/env bash
set -euo pipefail
mkdir -p /data/spool /data/output /data/channel/checkpoint /data/channel/data /logs
export FLUME_LOG_DIR=/logs
exec /opt/flume/bin/flume-ng agent \
  --name a1 --conf /opt/flume/conf --conf-file /project/config/flume.conf \
  -Dflume.root.logger=INFO,console
