# ODROID HC4 OLED Stats

A modified version of [tobetter/odroid-homecloud](https://github.com/tobetter/odroid-homecloud)
that shows system statistics on the ODROID HC4 OLED display. The original
history and MIT license are preserved; see [LICENSE](./LICENSE).

Although this repository has a different name, the Debian package
`odroid-homecloud-display`, command `odroid_homecloud_display`, and systemd
service `odroid-homecloud-display` retain their original names so existing
installations can be upgraded. The current version is `0.4.1`.

## What appears on the screen

The program uses a 128 x 64 pixel I2C SSD1306 display with four lines per page.
It updates CPU and RAM approximately once per second and switches pages every
five seconds. External commands can add some delay.
**This version displays statistics, not the original project's clock.**

An illustrative first page (these are not readings from your ODROID):

```text
CPU: 12%  48 C
RAM: 1,2 / 4,0 GB
sd: 8,5 / 31,3 GB
tank: 450,0 / 2000,0 GB
```

- CPU: usage between two `/proc/stat` samples, followed by the temperature
  from `/sys/class/thermal/thermal_zone0/temp`, or `N/A` if unavailable.
- RAM: used memory, calculated as `MemTotal - MemAvailable`, and total memory.
- `sd`: usage of the filesystem mounted at `/`, even if it is not an SD card.
- `tank`: ZFS `used` and `used + available` for the selected dataset, which
  defaults to `tank`. This is not a sum of physical disk capacities.
  Set `HOMECLOUD_ZFS_DATASET` to change the dataset and its screen label;
  see [ZFS configuration](#selecting-a-zfs-pool-or-dataset).
  If ZFS or the selected dataset is unavailable, this line reads
  `<dataset>: unavailable`. ZFS is optional; do not install it solely to
  run the display.
- GB is decimal (`1 GB = 1,000,000,000 bytes`). The display retains comma
  decimal separators. Long lines are compressed horizontally to preserve
  all digits.

Network pages follow, for example:

```text
IPv4: 192.0.2.10
IPv6: eth0
2001:4860:1234:5678:
abcd:ef01:2345:6789
```

The IPv4 address above is reserved for documentation; the IPv6 address is
illustrative. IPv6 line breaks depend on the installed font, so your device
may split it differently. The second line identifies the interface.
The program includes IPv4 and only global, non-temporary IPv6 addresses.
It skips loopback, interfaces whose names start with `docker`, `br-`, or `veth`,
and tentative addresses or addresses that failed duplicate address detection.

Each interface/address can produce additional pages. IPv6 addresses are split
into blocks of up to two lines. A missing address family is shown as
`unavailable`. With no eligible addresses, the page contains `IPv4: unavailable`
and `IPv6: unavailable`; if the network query fails, it shows `IP: unavailable`.
After the network pages, the cycle returns to system statistics.

## Build on another machine (Linux or WSL)

Use Debian/Ubuntu with `debhelper` 13 and `pybuild-plugin-pyproject` available,
such as Ubuntu 24.04, which is also used by the pipeline. The build machine
does not need an OLED, I2C hardware, a running systemd instance, or an ARM CPU.

This is a pure Python package with `Architecture: all`. You can build it on
WSL/x86_64 and install it on the ODROID/ARM64. APT resolves native dependencies
**on the ODROID**, using the ODROID's architecture.

### 1. Install build tools with sudo

On the build machine:

```sh
sudo apt update
sudo apt install git build-essential debhelper dh-python \
  pybuild-plugin-pyproject python3-all python3-setuptools \
  python3-wheel
```

To transfer the package using SCP or SFTP, also install the SSH client:

```sh
sudo apt install openssh-client
```

### 2. Clone your fork inside your home directory

On WSL, use the Linux filesystem (`~/build`), not `/mnt/c`, to avoid permission,
performance, and line-ending issues.

```sh
mkdir -p ~/build
cd ~/build
git clone https://github.com/joaomorenorf/odroid-hc4-oled-stats.git
cd odroid-hc4-oled-stats
```

**The old file-update block is no longer needed.** The Python 3, pyproject,
and debhelper changes are already tracked in this fork, including for WSL.
Cloning `tobetter/odroid-homecloud` directly does not include these changes
or the modified statistics monitor.

### 3. Build the package without sudo

```sh
dpkg-buildpackage -us -uc -b
ls -lh ../odroid-homecloud-display_*.deb
dpkg-deb --field ../odroid-homecloud-display_0.4.1_all.deb Package Version Architecture Depends
```

This version produces `../odroid-homecloud-display_0.4.1_all.deb`.
The parent directory also receives `.changes` and `.buildinfo` files.
Do not commit these files or temporary build directories.
The build does not install or start the service on the packaging machine.

### 4. Transfer the package to the ODROID

Replace `ODROID_IP` with the actual address. SSH must be enabled on the ODROID;
verify the server's identity when connecting for the first time.
Choose **one** of the following methods. Adjust the version in the filename
when using a different release.

**SCP:**

```sh
scp ../odroid-homecloud-display_0.4.1_all.deb root@ODROID_IP:/root/
```

**Interactive SFTP:**

```sh
sftp root@ODROID_IP
```

At the `sftp>` prompt, starting from the project directory on the build machine:

```text
lcd ..
cd /root
put odroid-homecloud-display_0.4.1_all.deb
bye
```

You do not need to enable SSH root login. If it is disabled, transfer the file
to a regular user instead:

```sh
scp ../odroid-homecloud-display_0.4.1_all.deb USER@ODROID_IP:
```

For SFTP as a regular user, connect with `sftp USER@ODROID_IP`, then run
`lcd ..`, `put odroid-homecloud-display_0.4.1_all.deb`, and `bye`; omit `cd /root`.

### 5. Install and validate on the ODROID

In the ODROID terminal, as root:

```sh
apt update
apt install /root/odroid-homecloud-display_0.4.1_all.deb
systemctl status odroid-homecloud-display --no-pager
```

Or, if you transferred the file to a regular user, from that user's home:

```sh
sudo apt update
sudo apt install ./odroid-homecloud-display_0.4.1_all.deb
sudo systemctl status odroid-homecloud-display --no-pager
```

APT installs Pillow, luma, and `iproute2` for the ODROID's architecture.
Do not run `pip` as root. If a dependency is unavailable, check your
distribution's repositories; Ubuntu may require enabling `universe`.
The target must run a Debian/Ubuntu release that provides the dependencies
declared by the package.

The debhelper installation scripts enable/start the service, subject to local
service policy. Check both the service status and the physical screen:
building a `.deb` on WSL does not validate the ODROID's hardware or I2C setup.

## Configuration and diagnostics

The first installation creates `/etc/default/odroid-homecloud` with these
defaults, without overwriting an existing configuration:

```sh
HOMECLOUD_DISPLAY_PORT=0
HOMECLOUD_DISPLAY_ROTATE=2
HOMECLOUD_DISPLAY_ADDRESS=0x3c
HOMECLOUD_ZFS_DATASET=tank
```

The display settings select the I2C bus, rotation (0 to 3, in 90-degree steps),
and hexadecimal device address. The driver is `ssd1306`; there is no automatic
chipset selection. An incorrect address or driver can prevent the display
from working.

### Selecting a ZFS pool or dataset

`HOMECLOUD_ZFS_DATASET` selects the **ZFS dataset name**, not a disk device
such as `/dev/sda`. A pool's root dataset, such as `backup`, is valid, as is a
child dataset such as `tank/media`. List available names on the ODROID:

```sh
sudo zfs list -o name,used,available
sudoedit /etc/default/odroid-homecloud
```

For example, add or change this line:

```sh
HOMECLOUD_ZFS_DATASET=backup
```

The corresponding display line will look like:

```text
backup: 450,0 / 2000,0 GB
```

For a child dataset, use `HOMECLOUD_ZFS_DATASET=tank/media`; the label becomes
`tank/media`. Long labels are compressed along with the rest of the line.

**Upgrading an existing installation:** the package preserves your current
configuration file. Add `HOMECLOUD_ZFS_DATASET=...` yourself to select another
dataset. If the variable is absent, the program continues using `tank`.
Do not leave the value empty; an empty value is a configuration error
reported in the service journal.

Restart the service after changing any setting:

```sh
sudo systemctl restart odroid-homecloud-display
sudo systemctl status odroid-homecloud-display --no-pager
sudo journalctl -u odroid-homecloud-display -n 50 --no-pager
ls -l /dev/i2c-*
```

### Print the actual display lines without accessing the OLED

After installation, run this on the ODROID. It loads the settings from
`/etc/default/odroid-homecloud`, including the selected ZFS dataset.
Keep that file in the simple shell-compatible `NAME=value` format shown above.

```sh
sudo sh -c 'set -a; . /etc/default/odroid-homecloud; exec python3 -' <<'PY'
import time
from odroid_homecloud_display import clock

previous = clock.cpu_sample()
time.sleep(1)
current = clock.cpu_sample()
total = current[0] - previous[0]
idle = current[1] - previous[1]
cpu = 100 * (1 - idle / total) if total else 0
used, capacity = clock.ram_usage()
pages = [[
    f"CPU: {cpu:.0f}%  {clock.temperature()}",
    f"RAM: {clock.decimal(used / 1e9)} / {clock.decimal(capacity / 1e9)} GB",
    *clock.storage_lines(),
]] + clock.network_pages(128)
for index, lines in enumerate(pages, 1):
    print(f"--- Page {index} ---")
    print("\n".join(lines))
PY
```

This prints a snapshot of the logical lines, not a pixel capture. Values change
over time, and long lines may be compressed when rendered.
Review IP addresses and interface names before sharing the output.

## Pipeline: build the .deb on GitHub

The [Build Debian package](./.github/workflows/build-deb.yml) workflow runs on
Ubuntu 24.04 for every push and pull request. You can also run it manually:

1. Open **Actions > Build Debian package > Run workflow** in your repository.
2. Select the branch and start the workflow.
3. Open the successful run and download **odroid-homecloud-display-deb**
   from its artifacts.
4. Extract the ZIP; it contains the `.deb` and `SHA256SUMS`.
5. Run `sha256sum -c SHA256SUMS` in the extracted directory, then transfer the
   `.deb` using SCP or SFTP as described above.

You can also use the GitHub CLI:

```sh
gh workflow run build-deb.yml --repo joaomorenorf/odroid-hc4-oled-stats
gh run list --workflow build-deb.yml --repo joaomorenorf/odroid-hc4-oled-stats
gh run download RUN_ID --repo joaomorenorf/odroid-hc4-oled-stats \
  --name odroid-homecloud-display-deb --dir artifacts/RUN_ID
cd artifacts/RUN_ID
sha256sum -c SHA256SUMS
```

Replace both occurrences of `RUN_ID` in the download command and the directory
name with the successful run's ID. Use a fresh directory for each download:
`gh run download` does not overwrite existing files.

The pipeline retains artifacts for 30 days. It does not install anything on
the ODROID, create a GitHub Release, or increment the version automatically.
New forks may require enabling Actions first.

### Future versions

Update the version in both [setup.py](./setup.py) and the first entry of
[debian/changelog](./debian/changelog), describe the changes, and push a commit.
The next push builds a package with that version. Increment it so APT recognizes
updates. The workflow checks that the Python and Debian versions match and
verifies the resulting package's version and architecture.

## Tests

Run the focused storage tests without an OLED, ZFS installation, or third-party
Python dependencies:

```sh
python3 -m unittest discover -s tests -v
```

The tests isolate display-library imports and mock storage queries. They check
the default dataset, configured pools and child datasets, screen labels, and
failure cases; they do not validate the physical display.
The Debian build also runs these tests through pybuild.

## Repository sources and local artifacts

Python source, tests, `pyproject.toml`, `setup.py`, packaging sources in `debian/`,
documentation, the license, and the workflow belong in the repository.
[.gitignore](./.gitignore) excludes caches, virtual environments, Python build
metadata, debhelper staging files, packages, and other build output. These can
remain on your machine without being published in the fork.

The original project is
[tobetter/odroid-homecloud](https://github.com/tobetter/odroid-homecloud).
The installed package includes its credits and MIT terms in
`/usr/share/doc/odroid-homecloud-display/copyright`.
