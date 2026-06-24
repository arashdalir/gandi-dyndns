#!/usr/bin/env python3
"""
Gandi Dynamic DNS Installer - Systemd service setup with dynamic paths
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


class GandiDNSInstaller:
    def __init__(self, config_path=None):
        self.script_dir = Path(__file__).parent.absolute()
        self.script_path = self.script_dir / "update_dns.py"

        # Use provided config path or default to config.json in script dir
        if config_path:
            self.config_path = Path(config_path).absolute()
        else:
            self.config_path = self.script_dir / "config.json"

        self.example_config_path = self.script_dir / "config.example.json"

    def print_header(self, text):
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")

    def print_success(self, text):
        print(f"✓ {text}")

    def print_error(self, text):
        print(f"✗ {text}")

    def print_warning(self, text):
        print(f"⚠ {text}")

    def print_info(self, text):
        print(f"ℹ {text}")

    def check_python(self):
        """Verify Python 3 is available."""
        if sys.version_info < (3, 6):
            self.print_error("Python 3.6+ is required")
            sys.exit(1)
        self.print_success(f"Python {sys.version.split()[0]} found")

    def check_script(self):
        """Verify the script exists."""
        if not self.script_path.exists():
            self.print_error(f"Script not found: {self.script_path}")
            sys.exit(1)
        self.print_success(f"Script found: {self.script_path}")

    def check_config(self):
        """Verify or create config file."""
        if self.config_path.exists():
            self.print_success(f"Config found: {self.config_path}")
            return True

        # Only auto-create if config is in the script directory
        if self.config_path.parent == self.script_dir and self.example_config_path.exists():
            self.print_warning("Config not found, creating from example...")
            with open(self.example_config_path) as f:
                example = f.read()
            with open(self.config_path, "w") as f:
                f.write(example)
            self.print_success(f"Config created: {self.config_path}")
            self.print_warning("Please edit it with your Gandi API key and domain")
            return False
        else:
            self.print_error(f"Config not found: {self.config_path}")
            self.print_info(f"Create a config file or use: --config /path/to/config.json")
            sys.exit(1)

    def generate_service_file(self):
        """Generate systemd service file with dynamic paths."""
        service_content = f"""[Unit]
Description=Gandi Dynamic DNS Updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory={self.script_dir}
ExecStart=/usr/bin/python3 {self.script_path} {self.config_path}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        return service_content

    def generate_timer_file(self):
        """Generate systemd timer file."""
        timer_content = """[Unit]
Description=Gandi Dynamic DNS Updater Timer
Requires=gandi-dyndns.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=1s

[Install]
WantedBy=timers.target
"""
        return timer_content

    def is_root(self):
        """Check if running as root."""
        return os.geteuid() == 0 if hasattr(os, "geteuid") else os.getuid() == 0

    def install_system_files(self):
        """Install service and timer files to systemd."""
        if not self.is_root():
            self.print_error("Root privileges required to install systemd files")
            self.print_info("Try: sudo python3 install.py")
            return False

        service_content = self.generate_service_file()
        timer_content = self.generate_timer_file()

        service_path = Path("/etc/systemd/system/gandi-dyndns.service")
        timer_path = Path("/etc/systemd/system/gandi-dyndns.timer")

        try:
            with open(service_path, "w") as f:
                f.write(service_content)
            self.print_success(f"Installed: {service_path}")

            with open(timer_path, "w") as f:
                f.write(timer_content)
            self.print_success(f"Installed: {timer_path}")

            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            self.print_success("Systemd daemon reloaded")

            # Enable and start timer
            subprocess.run(["systemctl", "enable", "gandi-dyndns.timer"], check=True)
            self.print_success("Timer enabled")

            subprocess.run(["systemctl", "start", "gandi-dyndns.timer"], check=True)
            self.print_success("Timer started")

            return True

        except PermissionError:
            self.print_error("Permission denied writing to /etc/systemd/system/")
            return False
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to run systemctl: {e}")
            return False

    def show_installation_instructions(self):
        """Show manual installation instructions."""
        service_content = self.generate_service_file()
        timer_content = self.generate_timer_file()

        print("\n" + "="*60)
        print("  Manual Installation Instructions")
        print("="*60 + "\n")

        print(f"Config file: {self.config_path}\n")

        print("1. Copy the following service file to /etc/systemd/system/gandi-dyndns.service:")
        print("\n" + "-"*60)
        print(service_content)
        print("-"*60 + "\n")

        print("2. Copy the following timer file to /etc/systemd/system/gandi-dyndns.timer:")
        print("\n" + "-"*60)
        print(timer_content)
        print("-"*60 + "\n")

        print("3. Then run:")
        print("   sudo systemctl daemon-reload")
        print("   sudo systemctl enable gandi-dyndns.timer")
        print("   sudo systemctl start gandi-dyndns.timer")
        print()

    def show_next_steps(self):
        """Show next steps after installation."""
        print("\n" + "="*60)
        print("  Next Steps")
        print("="*60 + "\n")

        if not self.config_path.exists():
            print(f"1. Create the configuration:")
            print(f"   nano {self.config_path}")
            print()

        print(f"2. Edit the configuration (if needed):")
        print(f"   nano {self.config_path}")
        print()

        print("3. Check timer status:")
        print("   systemctl status gandi-dyndns.timer")
        print()

        print("4. View logs:")
        print("   journalctl -u gandi-dyndns.service -f")
        print()

        print("5. Manually trigger an update:")
        print("   systemctl start gandi-dyndns.service")
        print()

    def run(self):
        """Run the installation process."""
        self.print_header("Gandi Dynamic DNS Installer")

        print(f"Script directory: {self.script_dir}")
        print(f"Config file:      {self.config_path}\n")

        self.check_python()
        self.check_script()
        config_exists = self.check_config()

        if not config_exists:
            self.print_warning("Please configure the script before installing the service")
            print()
            return

        # Try system installation
        if self.install_system_files():
            self.print_header("Installation Successful!")
            self.show_next_steps()
        else:
            self.print_warning("Could not install systemd files automatically")
            self.show_installation_instructions()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Install Gandi Dynamic DNS as a systemd service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python3 install.py
    Install with config.json in the script directory

  sudo python3 install.py --config /etc/dyndns/config.json
    Install with a custom config file location

  sudo python3 install.py --config /home/user/configs/my-domain.json
    Install with a custom config file path
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file (default: config.json in script directory)",
    )

    args = parser.parse_args()
    installer = GandiDNSInstaller(config_path=args.config)
    installer.run()
