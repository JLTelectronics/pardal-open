# Bootloader, unlocking and recovery

This page covers two situations: installing Pardal on an **existing DASH01**, and the
**custom Pardal hardware**, which is designed to be always unlockable.

## The DASH01: installing via the MediaTek service mode
The installer does not unlock the bootloader and does not change the device's security settings.
Instead it uses the standard USB service mode of the MediaTek chip (BROM), through the open-source
tool [mtkclient](https://github.com/bkerler/mtkclient). This is the same mode used for factory
programming and repairs.

With the installer you can:
- make a **complete backup** of your own device;
- install the Pardal boot system;
- **always return** to the factory state from that backup.

Entering service mode: start an installer command and then cut power to the device
(USB-C out, 2-3 s, back in), without pressing any buttons. mtkclient picks up the connection by itself.

> The installer never writes the lock state (`seccfg`) or the modem and identity partitions of your device.

## Pardal hardware: deliberately always unlockable
The custom hardware (see [`hardware/`](../hardware/)) is designed so that you are in charge of
your own device.

- **Rockchip RK3566 (Radxa CM3):** the bootloader (U-Boot) is open and always unlockable.
  Recovery without a working bootloader via **Rockusb/Loader mode** (recovery button while
  powering on) or automatically via **Maskrom** with empty/broken storage. Flash with
  `rkdeveloptool` / `upgrade_tool` over USB-C.
- **GSIs run** on the RK3566 (Treble), as does a custom Android build.
- **Never blow the secure-boot fuses**, so the chip always accepts your own bootloader.
- A **recovery button behind a pinhole** and a debug UART on test points, so the
  device is **unbrickable**.
