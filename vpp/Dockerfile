FROM ubuntu:20.04

# Install basic tools and VPP
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl gnupg nano procps openssh-server kmod \
    python3 python3-pip \
    && curl -s https://packagecloud.io/install/repositories/fdio/release/script.deb.sh | bash \
    && apt-get update \
    && apt-get install -y git vpp vpp-plugin-core vpp-plugin-dpdk iproute2 \
    && apt-get clean

# Creating log path
RUN mkdir -p /var/log/vpp

# Install Python dependencies for Prometheus exporter
RUN pip3 install prometheus_client vpp_papi

RUN apt-get update && apt-get install -y \
    build-essential \
    ninja-build \
    nasm \
    clang \
    nasm \
    libnuma-dev \
    pkg-config \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

#RUN cd /tmp && git clone -b stable/2506 https://github.com/FDio/vpp.git
#RUN cd /tmp/vpp 
#RUN pip3 install ply
#RUN cd /tmp/vpp && sed -i 's/@sudo -E/@$(SUDO)/g' Makefile
#RUN cd /tmp/vpp && DEBIAN_FRONTEND=noninteractive make SUDO="" UNATTENDED="y" install-dep
#RUN cd /tmp/vpp && make install-dep
#RUN cd /tmp/vpp && /bin/sh ./extras/vagrant/build.sh
#RUN cd /tmp/vpp/build-root && dpkg -i *.deb

# Add the VPP exporter script
COPY vpp-exporter.py /usr/local/bin/vpp-exporter.py
COPY startup.conf /home/startup.conf
COPY startup.conf /etc/vpp/startup.conf
COPY startup-interfaces.vpp /etc/vpp/startup-interfaces.vpp

# Expose VPP Exporter port
EXPOSE 9191

# Start VPP and Exporter
CMD /bin/bash -c "vpp -c /home/startup.conf & sleep 50 && python3 /usr/local/bin/vpp-exporter.py"
