# Cisco Network Device Configuration & Vulnerability Assessment Tool 🛠️

## Overview 🌟

This web application simplifies the configuration and vulnerability assessment of Cisco network devices. It aims to make network management more efficient, secure, and user-friendly, reducing the need for manual CLI configurations.

## Key Features ✨

*   **Web-Based Configuration:** Configure Cisco devices through an intuitive web interface, eliminating the need for complex CLI commands. 🖱️
*   **Multi-Device Management:** Configure multiple devices simultaneously using parallel processing, saving time and ensuring consistent configurations. ⚙️
*   **Vulnerability Assessment:** Automatically identify potential security vulnerabilities in device configurations. 🛡️
*   **VLAN Management:** Easily create, modify, and manage VLANs with custom naming and batch updates. 🌐
*   **Network Protocol Configuration:** Configure essential network protocols such as Spanning Tree, Aggregation, and Routing Protocols. 🚦
*   **Device Management:** Add, edit, and remove device information within the system. ➕ ➖ ✏️
*   **SNMP Monitoring**: Use SNMP to show device information like name, location, interface status, etc. 📊
*   **Security Enhancement**: Password encryption, unused port status, and connection timeout. 🔒

## Benefits 🎉

*   **Time Efficiency:** Parallel processing and bulk configuration capabilities significantly reduce setup time. ⏱️
*   **Consistency:** Ensure uniform configurations across all devices. ✅
*   **Scalability:** Easily manage growing networks with multiple devices. 📈
*   **Enhanced Security:** Proactively identify and address potential security threats. 🔥
*   **Reduced Errors:** User-friendly interface minimizes configuration errors. 🚫

## Core Functionality ⚙️

*   **Console Port Configuration:** Initial configuration system for new network devices via serial port connection. 💻
*   **Web Interface Configuration:** Streamlined setup process through a user-friendly web UI. 🌐
*   **Automated Setup Process:** Automate repetitive configuration tasks. 🤖
*   **Network Integration:** Seamlessly integrate new devices into existing networks. 🔗

## Device Management Features 🖥️

*   **Device Information Input:**
    *   Enter device name, IP address, username, password, and privilege mode password.
    *   Securely store device information in the database.
*   **Device Management Interface:**
    *   View and manage network devices.
    *   Edit device information.
    *   Remove devices from the system.
    *   Test device connectivity using Ping.

## Network Configuration 🌐

*   **Basic Settings:**
    *   Hostname configuration.
    *   Secret password setup.
    *   Banner configuration.
*   **Interface Settings:**
    *   IPv4/IPv6 configuration.
    *   DHCP configuration.
    *   Interface status control.
    *   Duplex mode selection.
*   **VLAN Configuration:**
    *   VLAN creation.
    *   Status control.
    *   VLAN naming.
    *   VLAN removal.
    *   Port configuration (Access/Trunk).
*   **Management Settings:**
    *   Line configuration (Console/VTY).
    *   DHCP configuration.
    *   NTP settings.
    *   SNMP configuration.
    *   Discovery protocols (CDP/LLDP).
*   **Routing Protocols:**
    *   Static route configuration.
    *   OSPF protocol.
    *   RIPv2 protocol.
    *   EIGRP protocol.

## Security Audit & Device Control 🛡️

*   **Security Audit:** Automated vulnerability detection.
*   **Device Control:**
    *   Factory reset.
    *   Device reload.
    *   Database removal on reset.
    *   Password encryption.
    *   Unused port status.
    *   Connection timeout.

## Multi-Device Configuration 🔄

Configure multiple devices simultaneously using threading for parallel processing, which improves time efficiency, ensures consistency, and enhances scalability.

## SNMP Device Information 📊

Retrieve device information using SNMP queries:

*   Device Identity.
*   System Information.
*   Interface Details.

## Installation 🚀

1.  **Download the application:** See the download table below.
2.  **Install Dependencies:** Make sure you have all the necessary libraries installed.
3.  **Configure MongoDB:**

    *   This application uses MongoDB to store device information.
    *   Ensure your MongoDB instance is installed and running.
    *   Set the `MONGO_URI` in your configuration file with the following format:

    ```
    mongodb://username:password@host:port/database
    ```

    *   Example: `mongodb://admin:secret@localhost:27017/network_config`

    *   **Example MongoDB Device Document Structure:**

        ```
        {
            "_id": ObjectId('67970f2d3e7eb368814f9c9c'),
            "name": "SW1",
            "timestamp": "2025-01-25T18:24:44",
            "device_info": {
                "device_type": "cisco_ios",
                "ip": "10.0.0.101",
                "username": "admin",
                "password": "admin",
                "secret": "admin"
            },
            "session_log": "output.log",
            "analysis": {
                "warnings": []
            },
            "last_updated": "2025-01-29 21:45:51"
        }
        ```
4.  **Run the Application:** Follow the instructions in the documentation to start the web application.

## Download Link 🔗

| Item         | Link                                                                                                                                      |
| :----------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| **Download** | [Cisco Config Tool](https://drive.google.com/file/d/1DBnpDx42aEkgpKMNdnEWmRzKJbWWccOm/view) 💾  |

## Key Technologies 💻

*   **Frontend:** Flask Web Framework
*   **Network Interaction:** Netmiko Library
*   **Data Storage:** MongoDB Database
*   **Processing Features:** Python Threading, NLP Security Check
*   **Network Management:** Net-SNMP, Serial-Python

## Contributing 🤝

Feel free to contribute to the project! Fork the repository, make your changes, and submit a pull request.

![Screenshot description](screenshots/1.png)
![Screenshot description](screenshots/2.png)
