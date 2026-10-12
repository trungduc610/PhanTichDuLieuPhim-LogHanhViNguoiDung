FROM eclipse-temurin:8-jre-jammy
ARG FLUME_VERSION=1.11.0
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates python3 procps \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/flume-download
RUN curl -fSL --retry 3 "https://archive.apache.org/dist/flume/${FLUME_VERSION}/apache-flume-${FLUME_VERSION}-bin.tar.gz" -o flume.tar.gz \
    && curl -fSL --retry 3 "https://archive.apache.org/dist/flume/${FLUME_VERSION}/apache-flume-${FLUME_VERSION}-bin.tar.gz.sha512" -o flume.sha512
COPY scripts/verify_archive.py /tmp/verify_archive.py
RUN python3 /tmp/verify_archive.py flume.tar.gz flume.sha512 \
    && mkdir /opt/flume \
    && tar -xzf flume.tar.gz -C /opt/flume --strip-components=1 \
    && rm -rf /tmp/flume-download
ENV FLUME_HOME=/opt/flume
ENV FLUME_HEAP_OPTS="-Xms128m -Xmx512m"
COPY config/flume-env.sh /opt/flume/conf/flume-env.sh
COPY config/log4j2.xml /opt/flume/conf/log4j2.xml
COPY config/flume.conf /project/config/flume.conf
COPY scripts/run_flume.sh /project/scripts/run_flume.sh
RUN chmod +x /project/scripts/run_flume.sh
WORKDIR /project
ENTRYPOINT ["/bin/bash", "/project/scripts/run_flume.sh"]
