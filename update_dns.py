#!/usr/bin/env python3
"""
Gandi Dynamic DNS updater - Updates DNS A/AAAA records with current public IP
"""

import json
import sys
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime



class GandiDNSUpdater:
    API_BASE_URL = "https://api.gandi.net/v5/livedns/domains"
    IP_DETECT_V4 = "https://ifconfig.me"
    IP_DETECT_V6 = "https://ifconfig.me/ip"

    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.api_key = self.config.get("api_key")
        self.domain = self.config.get("domain")
        self.ttl = self.config.get("ttl", 3600)
        self.records = self.config.get("records", [])

    def _load_config(self, config_path):
        """Load configuration from JSON file."""
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging to stdout (systemd will capture and send to journal)."""
        logger = logging.getLogger("gandi-dyndns")
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def _get_public_ip(self, ip_version="v4"):
        """Detect public IP address."""
        try:
            if ip_version == "v6":
                response = requests.get(self.IP_DETECT_V6, timeout=5)
            else:
                response = requests.get(self.IP_DETECT_V4, timeout=5)

            response.raise_for_status()
            ip = response.text.strip()
            return ip
        except requests.RequestException as e:
            self.logger.error(f"Failed to detect public IP ({ip_version}): {e}")
            return None

    def _update_record(self, record_name, record_type, ip_address):
        """Update a DNS record via Gandi API."""
        url = (
            f"{self.API_BASE_URL}/{self.domain}/records/{record_name}/{record_type}"
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "rrset_values": [ip_address],
            "rrset_ttl": self.ttl,
        }

        try:
            response = requests.put(url, headers=headers, json=payload, timeout=10)

            if response.status_code in [200, 201]:
                self.logger.info(
                    f"✓ Updated {record_name}.{self.domain} ({record_type}): {ip_address}"
                )
                return True
            elif response.status_code == 409:
                self.logger.warning(
                    f"⚠ Conflict updating {record_name}.{self.domain} ({record_type}): {response.text}"
                )
                return False
            else:
                self.logger.error(
                    f"✗ Failed to update {record_name}.{self.domain} ({record_type}): "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return False

        except requests.RequestException as e:
            self.logger.error(
                f"✗ Network error updating {record_name}.{self.domain} ({record_type}): {e}"
            )
            return False

    def run(self):
        """Main execution: detect IPs and update all records."""
        self.logger.info(
            f"Starting DNS update for domain: {self.domain} ({len(self.records)} records)"
        )

        if not self.api_key:
            self.logger.error("API key not configured")
            return False

        if not self.records:
            self.logger.warning("No records configured to update")
            return True

        # Detect IPs
        ip_v4 = None
        ip_v6 = None

        # Separate records by type
        v4_records = [r for r in self.records if r.get("type") == "A"]
        v6_records = [r for r in self.records if r.get("type") == "AAAA"]

        if v4_records:
            ip_v4 = self._get_public_ip("v4")
            if not ip_v4:
                self.logger.error("Could not detect IPv4 address, skipping A records")

        if v6_records:
            ip_v6 = self._get_public_ip("v6")
            if not ip_v6:
                self.logger.warning(
                    "Could not detect IPv6 address, skipping AAAA records"
                )

        # Update records
        success_count = 0
        fail_count = 0

        for record in self.records:
            record_name = record.get("name")
            record_type = record.get("type", "A")

            if not record_name:
                self.logger.warning("Record missing 'name' field, skipping")
                continue

            if record_type == "A" and ip_v4:
                if self._update_record(record_name, record_type, ip_v4):
                    success_count += 1
                else:
                    fail_count += 1
            elif record_type == "AAAA" and ip_v6:
                if self._update_record(record_name, record_type, ip_v6):
                    success_count += 1
                else:
                    fail_count += 1
            elif record_type == "A" and not ip_v4:
                self.logger.error(
                    f"✗ Skipping A record {record_name}: IPv4 not detected"
                )
                fail_count += 1
            elif record_type == "AAAA" and not ip_v6:
                self.logger.error(
                    f"✗ Skipping AAAA record {record_name}: IPv6 not detected"
                )
                fail_count += 1

        self.logger.info(
            f"Update complete: {success_count} successful, {fail_count} failed"
        )
        return fail_count == 0


def main():
    parser = argparse.ArgumentParser(
        description="Update Gandi DNS records with current public IP"
    )
    parser.add_argument(
        "config",
        type=str,
        nargs="?",
        default="config.json",
        help="Path to configuration JSON file (default: config.json in current directory)",
    )

    args = parser.parse_args()

    updater = GandiDNSUpdater(args.config)
    success = updater.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
