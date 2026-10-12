#!/usr/bin/env bash
set -euo pipefail
role="${1:?namenode or datanode required}"
: "${HDFS_RUN_ID:?Use a dedicated HDFS run ID}"
[[ "$HDFS_RUN_ID" =~ ^hdfs-[a-f0-9]{12}$ ]] || { echo 'Invalid cluster ID'; exit 1; }
case "$role" in
  namenode) store=/hdfs/name ;;
  datanode) store=/hdfs/data ;;
  *) echo 'Unknown role'; exit 1 ;;
esac
mkdir -p "$store"
if [[ -f "$store/current/VERSION" ]]; then
  actual=$(sed -n 's/^clusterID=//p' "$store/current/VERSION")
  [[ "$actual" == "$HDFS_RUN_ID" ]] || { echo 'Cluster ID mismatch: refusing existing volume'; exit 1; }
  echo "REUSE_VERIFIED_VOLUME role=$role cluster=$actual"
elif [[ -n "$(find "$store" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Refusing non-empty unformatted $role volume"; exit 1
elif [[ "$role" == namenode ]]; then
  echo "FORMAT_NEW_EMPTY_VOLUME role=$role cluster=$HDFS_RUN_ID"
  hdfs namenode -format -clusterId "$HDFS_RUN_ID" -nonInteractive
else
  echo "NEW_EMPTY_VOLUME role=$role cluster=$HDFS_RUN_ID"
fi
exec hdfs "$role"
