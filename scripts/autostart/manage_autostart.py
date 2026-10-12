"""
Cross-Platform Autostart Manager for AutoInsta
Supports: Windows, macOS, Linux (systemd), and Android (Termux:Boot)
"""

import sys
import os
import platform
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def is_android():
    return "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")

def setup_windows(enable=True):
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    bat_file = startup_dir / "AutoInsta_Autostart.bat"
    
    if enable:
        python_exe = sys.executable
        content = f'@echo off\r\ncd /d "{BASE_DIR}"\r\nstart "" /b "{python_exe}" -m uvicorn server.app:app --host 0.0.0.0 --port 8000\r\n'
        startup_dir.mkdir(parents=True, exist_ok=True)
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Windows autostart enabled successfully via Startup shortcut: {bat_file}")
    else:
        if bat_file.exists():
            bat_file.unlink()
            print("[-] Windows autostart disabled and shortcut removed.")
        else:
            print("[-] Windows autostart was not active.")

def setup_macos(enable=True):
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    plist_file = launch_agents / "dev.silveremartin.autoinsta.plist"
    
    if enable:
        launch_agents.mkdir(parents=True, exist_ok=True)
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>dev.silveremartin.autoinsta</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>server.app:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{BASE_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
        with open(plist_file, "w", encoding="utf-8") as f:
            f.write(plist_content)
        os.system(f"launchctl load {plist_file}")
        print(f"[+] macOS autostart enabled (LaunchAgent installed: {plist_file})")
    else:
        if plist_file.exists():
            os.system(f"launchctl unload {plist_file} 2>/dev/null")
            plist_file.unlink()
            print("[-] macOS autostart disabled and LaunchAgent removed.")
        else:
            print("[-] macOS autostart was not active.")

def setup_linux(enable=True):
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    service_file = systemd_dir / "autoinsta.service"
    
    if enable:
        systemd_dir.mkdir(parents=True, exist_ok=True)
        service_content = f"""[Unit]
Description=AutoInsta POV Lifelogger & Social Agent
After=network.target

[Service]
Type=simple
WorkingDirectory={BASE_DIR}
ExecStart={sys.executable} -m uvicorn server.app:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=default.target
"""
        with open(service_file, "w", encoding="utf-8") as f:
            f.write(service_content)
        os.system("systemctl --user daemon-reload")
        os.system("systemctl --user enable --now autoinsta.service")
        print(f"[+] Linux systemd autostart enabled: {service_file}")
    else:
        if service_file.exists():
            os.system("systemctl --user stop autoinsta.service 2>/dev/null")
            os.system("systemctl --user disable autoinsta.service 2>/dev/null")
            service_file.unlink()
            os.system("systemctl --user daemon-reload")
            print("[-] Linux systemd autostart disabled and removed.")
        else:
            print("[-] Linux autostart was not active.")

def setup_android(enable=True):
    boot_dir = Path.home() / ".termux" / "boot"
    boot_file = boot_dir / "autoinsta_boot.sh"
    
    if enable:
        boot_dir.mkdir(parents=True, exist_ok=True)
        content = f"""#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd "{BASE_DIR}" || cd "$HOME/AutoInsta"
python client/android_termux/autoinsta_capture.py > "$HOME/autoinsta_boot.log" 2>&1 &
"""
        with open(boot_file, "w", encoding="utf-8") as f:
            f.write(content)
        os.system(f"chmod +x {boot_file}")
        print(f"[+] Android Termux:Boot enabled ({boot_file})")
        print("[!] Requires the 'Termux:Boot' companion app installed on your phone.")
    else:
        if boot_file.exists():
            boot_file.unlink()
            print("[-] Android Termux:Boot autostart removed.")
        else:
            print("[-] Android autostart was not active.")

def main():
    parser = argparse.ArgumentParser(description="AutoInsta Multiplatform Autostart Manager")
    parser.add_argument("--enable", action="store_true", help="Enable and register autostart at login/boot")
    parser.add_argument("--disable", action="store_true", help="Disable and completely remove autostart")
    parser.add_argument("--status", action="store_true", help="Check current autostart status")
    args = parser.parse_args()

    if not (args.enable or args.disable or args.status):
        parser.print_help()
        sys.exit(1)

    os_name = "Android" if is_android() else platform.system()
    print(f"[*] Detected Environment: {os_name}")

    action_enable = args.enable and not args.disable

    if os_name == "Windows":
        setup_windows(enable=action_enable)
    elif os_name == "Darwin":
        setup_macos(enable=action_enable)
    elif os_name == "Android":
        setup_android(enable=action_enable)
    elif os_name == "Linux":
        setup_linux(enable=action_enable)
    else:
        print(f"[!] Unsupported operating system: {os_name}")

if __name__ == "__main__":
    main()
