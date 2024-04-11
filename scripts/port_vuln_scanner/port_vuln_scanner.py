#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple port scanner that scans the top 15 most common ports for open status and identifies potential vulnerabilities
based on the open ports found on a target IP address or domain name.

Usage:
    Run this script and enter the target website URL or IP address when prompted.
"""

__author__ = "Brad Kovaluk"
__email__ = "bkovaluk@gmail.com"
__date__ = "2024-01-11"
__version__ = "1.0.0"

import socket
import sys
import logging
from prettytable import PrettyTable

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dictionary mapping common ports to their respective vulnerabilities (Top 15)
vulnerabilities = {
    80: "HTTP (Hypertext Transfer Protocol) - Used for unencrypted web traffic",
    443: "HTTPS (HTTP Secure) - Used for encrypted web traffic",
    22: "SSH (Secure Shell) - Used for secure remote access",
    21: "FTP (File Transfer Protocol) - Used for file transfers",
    25: "SMTP (Simple Mail Transfer Protocol) - Used for email transmission",
    23: "Telnet - Used for remote terminal access",
    53: "DNS (Domain Name System) - Used for domain name resolution",
    110: "POP3 (Post Office Protocol version 3) - Used for email retrieval",
    143: "IMAP (Internet Message Access Protocol) - Used for email retrieval",
    3306: "MySQL - Used for MySQL database access",
    3389: "RDP (Remote Desktop Protocol) - Used for remote desktop connections (Windows)",
    8080: "HTTP Alternate - Commonly used as a secondary HTTP port",
    8000: "HTTP Alternate - Commonly used as a secondary HTTP port",
    8443: "HTTPS Alternate - Commonly used as a secondary HTTPS port",
    5900: "VNC (Virtual Network Computing) - Used for remote desktop access",
}


def display_table(open_ports):
    """
    Generates and prints a table of open ports along with their associated vulnerabilities.

    :param open_ports: List of open port numbers.
    """
    table = PrettyTable(["Open Port", "Vulnerability"])
    for port in open_ports:
        vulnerability = vulnerabilities.get(port, "No known vulnerabilities associated with common services")
        table.add_row([port, vulnerability])
    print(table)


def scan_top_ports(target):
    """
    Scans the top 15 common ports on the given target.

    :param target: Target IP address or domain name as a string.
    :return: List of open port numbers.
    """
    open_ports = []
    top_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 5900, 8000, 8080, 8443]  # Top 15 ports
    for port in top_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # Timeout can be adjusted
            result = sock.connect_ex((target, port))
            if result == 0:
                logging.info(f"Port {port} is open.")
                open_ports.append(port)
            sock.close()
        except KeyboardInterrupt:
            logging.error("Scan interrupted by user.")
            sys.exit()
        except socket.error as e:
            logging.warning(f"Failed to connect to port {port}: {e}")
    return open_ports


def main():
    """
    Main function that prompts the user for a target, performs a scan of the top 15 common ports,
    and displays any open ports with their associated vulnerabilities.
    """
    target = input("Enter the website URL or IP address to scan for open ports: ")
    logging.info(f"Scanning the top 15 ports on {target}")
    open_ports = scan_top_ports(target)
    if not open_ports:
        logging.info("No open ports found on the target.")
    else:
        logging.info("Open ports and associated vulnerabilities:")
        display_table(open_ports)


if __name__ == "__main__":
    main()
