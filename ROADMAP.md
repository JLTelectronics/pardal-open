# Roadmap

An honest overview: what works, what's coming, and where help is welcome (🙋).

## Works now
- Speedometer with max-speed sign, too-fast warning (calm: one beep).
- Speed cameras and average-speed (section) controls (OSM), road alerts and matrix signs (NDW/Rijkswaterstaat), KNMI weather.
- Report it yourself with three confirmations; offline map (2D/3D) from the RWS road dataset.
- 6 languages (NL, EN, DE, ES, PT, Frysk); light/dark theme.
- iOS with CarPlay.
- **DASH01:**
  - Android 13 with 4G (with your own data eSIM), Wi-Fi hotspot or Bluetooth tethering, GPS, Wi-Fi, Bluetooth, sound and charging;
  - starts straight into Pardal when the ignition comes on, screen off after 5 min without power, fully off after 2 hours;
  - custom boot logo and recovery screen.

## In progress
- **DASH01 installer** for Linux/macOS: backup → install → restore with a single command. 🙋 testers with their own
  DASH01.
- Custom open hardware: round 480×480 screen, open bootloader (always unlockable and recoverable). 🙋 PCB and an own enclosure design.

## Planned
- Android Auto. 🙋
- Data sources outside the Netherlands (Belgium, Germany). 🙋
- VoLTE on the DASH01 (calling isn't required, but the network asks for it more and more often).
- Self-hostable server with a simple `docker compose` guide.
- F-Droid.

## Known issues
- DASH01: surfaceflinger once used a lot of memory. This is now monitored and handled with a clean
  restart; the cause is being investigated.
- Mobile reports: the more users, the better. In the beginning you'll see few of them.
