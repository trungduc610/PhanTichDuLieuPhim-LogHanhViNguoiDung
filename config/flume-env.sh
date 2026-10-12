#!/usr/bin/env bash
# flume-ng sets its default JAVA_OPTS before sourcing this file.
export JAVA_OPTS="${FLUME_HEAP_OPTS:--Xms128m -Xmx512m} -XX:+PrintFlagsFinal"
export FLUME_JAVA_OPTS="${FLUME_JAVA_OPTS:-} -Dlog4j.configurationFile=/opt/flume/conf/log4j2.xml"
