import netifaces

# Get all interfaces
interfaces = netifaces.interfaces()

# Loop through all interfaces and get their IP addresses
for interface in interfaces:
    addresses = netifaces.ifaddresses(interface)
    if netifaces.AF_INET in addresses:  # IPv4
        for address in addresses[netifaces.AF_INET]:
            print(f"Interface: {interface} - IP Address: {address['addr']}")
