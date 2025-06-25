from vpp_papi import VPPApiClient
from prometheus_client import start_http_server, Gauge
import time
import os

POD_ID = os.popen("ip -4 addr show eth0 | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}'").read().strip()

# ====================
# Connect to VPP
# ====================
vpp = VPPApiClient(server_address="/run/vpp/api.sock")
try:
    vpp.connect("vpp-prometheus-exporter")
except Exception as e:
    print("Failed to connect to VPP:", e)
    exit(1)


# ====================
# Prometheus Metrics
# ====================
iface_rx_packets = Gauge('vpp_interface_rx_packets', 'RX packets per VPP interface', ['interface', 'pod_ip'])
iface_tx_packets = Gauge('vpp_interface_tx_packets', 'TX packets per VPP interface', ['interface', 'pod_ip'])
iface_rx_bytes = Gauge('vpp_interface_rx_bytes', 'RX bytes per VPP interface', ['interface', 'pod_ip'])
iface_tx_bytes = Gauge('vpp_interface_tx_bytes', 'TX bytes per VPP interface', ['interface', 'pod_ip'])

linux_iface_rx_packets = Gauge('linux_interface_rx_packets', 'RX packets per Linux interface', ['interface', 'pod_ip'])
linux_iface_tx_packets = Gauge('linux_interface_tx_packets', 'TX packets per Linux interface', ['interface', 'pod_ip'])
linux_iface_rx_bytes = Gauge('linux_interface_rx_bytes', 'RX bytes per Linux interface', ['interface', 'pod_ip'])
linux_iface_tx_bytes = Gauge('linux_interface_tx_bytes', 'TX bytes per Linux interface', ['interface', 'pod_ip'])


# ====================
# Parse VPP Interface Stats
# ====================
def parse_interface_stats(output):
    print(output)
    print()
    interfaces = {}
    current_iface = None

    for line in output.splitlines():
        line = line.strip()

        if line and not line.startswith(('rx', 'tx')):
            current_iface = line.split()[0]
            interfaces[current_iface] = {
                'rx_packets': 0,
                'tx_packets': 0,
                'rx_bytes': 0,
                'tx_bytes': 0
            }

        if current_iface:
            parts = line.split()
            if line.startswith('rx'):
                if line.startswith('rx packets'):
                    interfaces[current_iface]['rx_packets'] = int(parts[2])
                if line.startswith('rx bytes'):
                    interfaces[current_iface]['rx_bytes'] = int(parts[2])
            elif line.startswith('tx'):
                if line.startswith('tx packets'):
                    interfaces[current_iface]['tx_packets'] = int(parts[2])
                if line.startswith('tx bytes'):
                    interfaces[current_iface]['tx_bytes'] = int(parts[2])

    return interfaces


# ====================
# Get Linux Interface Stats
# ====================
def get_linux_interface_stats(interface):
    stats = ['rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes']
    results = {}

    for stat in stats:
        stat_path = f'/sys/class/net/{interface}/statistics/{stat}'
        try:
            with open(stat_path, 'r') as file:
                results[stat] = int(file.read().strip())
        except FileNotFoundError:
            raise ValueError(f"Interface '{interface}' or stat '{stat}' not found.")
        except Exception as e:
            raise RuntimeError(f"Error reading {stat} for interface {interface}: {e}")

    return results


# ====================
# Export Function
# ====================
def export_metrics():
    try:
        # Export VPP stats
        reply = vpp.api.cli_inband(cmd="show interface")
        output = reply.reply
        stats = parse_interface_stats(output)

        for iface, counters in stats.items():
            iface_rx_packets.labels(interface=iface, pod_ip=POD_ID).set(counters['rx_packets'])
            iface_tx_packets.labels(interface=iface, pod_ip=POD_ID).set(counters['tx_packets'])
            iface_rx_bytes.labels(interface=iface, pod_ip=POD_ID).set(counters['rx_bytes'])
            iface_tx_bytes.labels(interface=iface, pod_ip=POD_ID).set(counters['tx_bytes'])

        # Export Linux stats
        linux_interfaces = [iface for iface in os.listdir('/sys/class/net') if iface != 'lo']
        for iface in linux_interfaces:
            try:
                counters = get_linux_interface_stats(iface)

                linux_iface_rx_packets.labels(interface=iface, pod_ip=POD_ID).set(counters['rx_packets'])
                linux_iface_tx_packets.labels(interface=iface, pod_ip=POD_ID).set(counters['tx_packets'])
                linux_iface_rx_bytes.labels(interface=iface, pod_ip=POD_ID).set(counters['rx_bytes'])
                linux_iface_tx_bytes.labels(interface=iface, pod_ip=POD_ID).set(counters['tx_bytes'])

            except Exception as e:
                print(f"Error collecting Linux metrics for {iface}: {e}")

    except Exception as e:
        print(f"Error collecting metrics: {e}")


# ====================
# Start HTTP Exporter
# ====================
start_http_server(9191, addr="0.0.0.0")
print("VPP & Linux Prometheus exporter running on port 9191...")

# ====================
# Loop
# ====================
try:
    while True:
        export_metrics()
        time.sleep(5)  # scrape interval
except KeyboardInterrupt:
    print("Exporter stopped by user.")
finally:
    vpp.disconnect()

