# Rock5B NVMe Boot Setup

This guide documents how to set up a Radxa Rock5B to boot from NVMe SSD using
the [joshua-riek/ubuntu-rockchip](https://github.com/joshua-riek/ubuntu-rockchip)
Ubuntu images.

## Prerequisites

- Radxa Rock5B
- NVMe SSD installed in the M.2 slot
- SD card (16GB+) for initial setup
- Ubuntu image from joshua-riek releases

## Overview

The Rock5B boot order is: SPI NOR Flash -> SD Card -> eMMC -> NVMe

To boot directly from NVMe, you must:

1. Flash the U-Boot bootloader to SPI NOR flash
2. Write the Ubuntu image directly to the NVMe drive

**Important:** Do NOT try to rsync/copy files to NVMe. You must `dd` the entire
image to get the proper partition table and boot setup.

## Step-by-Step Instructions

### Step 1: Flash SD Card with Ubuntu Image

Download the latest Rock5B image:

```bash
wget https://github.com/Joshua-Riek/ubuntu-rockchip/releases/download/v2.4.0/ubuntu-24.04-preinstalled-server-arm64-rock-5b.img.xz
```

Flash to SD card (replace `/dev/diskX` with your SD card):

```bash
# macOS
diskutil unmountDisk /dev/diskX
xzcat ubuntu-24.04-preinstalled-server-arm64-rock-5b.img.xz | sudo dd of=/dev/rdiskX bs=4m status=progress
diskutil eject /dev/diskX

# Linux
xzcat ubuntu-24.04-preinstalled-server-arm64-rock-5b.img.xz | sudo dd of=/dev/sdX bs=4M status=progress
```

### Step 2: Boot from SD Card

1. Insert SD card into Rock5B
2. Power on
3. Wait for boot (first boot may take a few minutes)
4. SSH in (default credentials: `ubuntu:ubuntu`, will prompt for password change)

```bash
ssh ubuntu@<ip-address>
```

### Step 3: Flash SPI Bootloader

From the Rock5B (booted from SD card), flash U-Boot to SPI:

```bash
sudo dd if=/usr/lib/u-boot/rkspi_loader.img of=/dev/mtdblock0 conv=notrunc
```

This takes about 2 minutes. Wait for it to complete.

### Step 4: Write Ubuntu Image to NVMe

Copy the image to the Rock5B:

```bash
# From your workstation
scp ubuntu-24.04-preinstalled-server-arm64-rock-5b.img.xz ubuntu@<ip-address>:~
```

Write the image directly to NVMe:

```bash
# On the Rock5B
xz -dc ~/ubuntu-24.04-preinstalled-server-arm64-rock-5b.img.xz | sudo dd of=/dev/nvme0n1 bs=4M status=progress
```

### Step 5: Expand Filesystem (Optional)

The image includes `x-systemd.growfs` which should auto-expand on first boot.
If you want to expand manually before rebooting:

```bash
sudo growpart /dev/nvme0n1 2
sudo resize2fs /dev/nvme0n1p2
```

Note: If the kernel has stale partition info, this may fail. Just proceed to
reboot and the auto-expand will handle it.

### Step 6: Boot from NVMe

1. Shut down the Rock5B: `sudo poweroff`
2. Remove the SD card
3. Power on

The system will now boot from NVMe via the SPI bootloader.

### Step 7: Verify

After boot, verify you're running from NVMe:

```bash
df -h /
# Should show /dev/nvme0n1p2

lsblk
# Should show nvme0n1p2 mounted as /
```

Verify the full disk is available:

```bash
df -h /
# Should show ~900GB+ available for a 1TB drive
```

## Troubleshooting

### Node won't boot after changing boot config

If you manually edited `/boot/extlinux/extlinux.conf` and the node won't boot:

1. Flash a fresh SD card with the Ubuntu image
2. Boot from SD card
3. The SD card will boot independently
4. Fix the eMMC/NVMe boot config from there

### NVMe not detected

Check if NVMe is visible:

```bash
lsblk | grep nvme
lspci | grep -i nvme
```

Some NVMe drives have compatibility issues. Check the
[ubuntu-rockchip issues](https://github.com/Joshua-Riek/ubuntu-rockchip/issues)
for known problems.

### SPI loader file not found

Find the correct path:

```bash
dpkg -L u-boot-rock-5b | grep spi
```

The file is typically at `/usr/lib/u-boot/rkspi_loader.img`.

## References

- [joshua-riek/ubuntu-rockchip](https://github.com/joshua-riek/ubuntu-rockchip)
- [Issue #172 - Booting from NVMe](https://github.com/Joshua-Riek/ubuntu-rockchip/issues/172)
- [Discussion #998 - Rock 5B+ NVMe boot](https://github.com/Joshua-Riek/ubuntu-rockchip/discussions/998)
- [Radxa ROCK 5B Wiki](https://github.com/Joshua-Riek/ubuntu-rockchip/wiki/Radxa-ROCK-5B)
