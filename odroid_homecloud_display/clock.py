import ipaddress
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

PAGE_SECONDS = 5
FONT = ImageFont.load_default()
MEASURE = ImageDraw.Draw(Image.new("1", (1, 1)))


def command(args):
    return subprocess.check_output(
        args, text=True, timeout=3, stderr=subprocess.DEVNULL
    )


def decimal(value):
    return f"{value:.1f}".replace(".", ",")


def cpu_sample():
    with open("/proc/stat") as f:
        v = list(map(int, f.readline().split()[1:]))
    return sum(v[:8]), v[3] + v[4]


def ram_usage():
    values = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0])
    total = values["MemTotal"] * 1024
    used = total - values["MemAvailable"] * 1024
    return used, total


def temperature():
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text()
        return f"{int(raw) / 1000:.0f} C"
    except (OSError, ValueError):
        return "N/A"


def storage_lines():
    dataset = os.getenv("HOMECLOUD_ZFS_DATASET", "tank")
    if not dataset.strip():
        raise ValueError("HOMECLOUD_ZFS_DATASET must not be empty")

    try:
        sd = shutil.disk_usage("/")
        sd_line = (
            f"sd: {decimal(sd.used / 1e9)} / "
            f"{decimal(sd.total / 1e9)} GB"
        )
    except OSError:
        sd_line = "sd: unavailable"

    try:
        zfs = shutil.which("zfs") or "/usr/sbin/zfs"
        used, available = map(int, command([
            zfs, "list", "-Hp", "-o", "used,available", dataset
        ]).split())
        zfs_line = (
            f"{dataset}: {decimal(used / 1e9)} / "
            f"{decimal((used + available) / 1e9)} GB"
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        zfs_line = f"{dataset}: unavailable"

    return [sd_line, zfs_line]


def text_width(text):
    box = MEASURE.textbbox((0, 0), text, font=FONT)
    return box[2] - box[0]


def wrap(text, width):
    lines = []
    current = ""
    for char in text:
        if current and text_width(current + char) > width:
            lines.append(current)
            current = char
        else:
            current += char
    if current:
        lines.append(current)
    return lines


def network_pages(width):
    pages = []
    try:
        interfaces = json.loads(command(["ip", "-j", "addr", "show"]))
        for interface in interfaces:
            name = interface["ifname"]
            if name == "lo" or name.startswith(("docker", "br-", "veth")):
                continue

            ipv4s, ipv6s = [], []
            for address in interface.get("addr_info", []):
                family = address.get("family")
                flags = address.get("flags", [])
                if (address.get("tentative") or address.get("dadfailed")
                        or "tentative" in flags or "dadfailed" in flags):
                    continue

                if family == "inet" and address.get("scope") != "host":
                    ipv4s.append(address["local"])
                elif family == "inet6":
                    ipv6 = ipaddress.IPv6Address(address["local"])
                    temporary = (
                        address.get("temporary", False)
                        or address.get("secondary", False)
                        or "temporary" in flags
                        or "secondary" in flags
                    )
                    if ipv6.is_global and not temporary:
                        ipv6s.append(str(ipv6))

            if not ipv4s and not ipv6s:
                continue

            count = max(len(ipv4s), len(ipv6s))
            for index in range(count):
                ipv4 = ipv4s[index % len(ipv4s)] if ipv4s else "unavailable"
                ipv6 = ipv6s[index % len(ipv6s)] if ipv6s else "unavailable"
                chunks = wrap(ipv6, width)
                for offset in range(0, len(chunks), 2):
                    pages.append([
                        f"IPv4: {ipv4}",
                        f"IPv6: {name}",
                        *chunks[offset:offset + 2],
                    ])

        return pages or [["IPv4: unavailable", "IPv6: unavailable"]]
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return [["IP: unavailable"]]


def draw_page(device, lines):
    with canvas(device) as draw:
        for row, text in enumerate(lines[:4]):
            y = row * 16
            # Fit long storage rows on one line without dropping digits.
            box = MEASURE.textbbox((0, 0), text, font=FONT)
            width = max(1, box[2] - box[0])
            height = max(1, box[3] - box[1])
            if width <= device.width:
                draw.text((0, y), text, font=FONT, fill="white")
            else:
                strip = Image.new("1", (width, height))
                ImageDraw.Draw(strip).text(
                    (-box[0], -box[1]), text, font=FONT, fill="white"
                )
                strip = strip.resize((device.width, height))
                draw.bitmap((0, y + 2), strip, fill="white")


def main():
    serial = i2c(
        port=int(os.getenv("HOMECLOUD_DISPLAY_PORT", "0")),
        address=int(os.getenv("HOMECLOUD_DISPLAY_ADDRESS", "0x3c"), 16),
    )
    device = ssd1306(
        serial, rotate=int(os.getenv("HOMECLOUD_DISPLAY_ROTATE", "2"))
    )
    previous = cpu_sample()
    page = 0
    deadline = 0
    extras = []

    try:
        while True:
            time.sleep(1)
            current = cpu_sample()
            total = current[0] - previous[0]
            idle = current[1] - previous[1]
            cpu = 100 * (1 - idle / total) if total else 0
            previous = current
            used, capacity = ram_usage()

            now = time.monotonic()
            if now >= deadline:
                if extras:
                    page += 1
                storage = storage_lines()
                extras = network_pages(device.width)
                deadline = time.monotonic() + PAGE_SECONDS

            pages = [[
                f"CPU: {cpu:.0f}%  {temperature()}",
                f"RAM: {decimal(used / 1e9)} / {decimal(capacity / 1e9)} GB",
                *storage,
            ]] + extras

            draw_page(device, pages[page % len(pages)])
    finally:
        device.cleanup()


if __name__ == "__main__":
    main()
