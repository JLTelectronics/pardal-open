# Contributing to Pardal

Great that you want to help! Pardal is a calm, open-source co-pilot: no account, no ads, no trip history.
Contributions are welcome on three fronts.

## Where can you help?
| Area | Examples | Where |
|---|---|---|
| **Data / server** | sources for Belgium/Germany, better speed-camera data, NDW parsing | `server/app/` |
| **DASH01** | installer, testing on your device, power/sleep, VoLTE | `dash-pure/` |
| **Hardware** | custom round PCB, enclosure design | `hardware/` |
| **Testing** | driving and reporting what went wrong (without personal data) | Issues |

Issues labelled **good first issue** are small and well scoped: a nice place to start.

> The **app source code** (iOS + Android) is still closed for now and will be opened up later. Until then,
> app ideas (features, Android Auto, translations) go through Issues/Discussions.

## Ground rules
- **No Flitsmeister code, APIs, data or firmware.** Not even "just for comparison". Pardal is independent.
- **No device data in issues or PRs:** no IMEI, serial number, eSIM or NV dumps, Wi-Fi passwords or logs
  that contain them.
- **Privacy is a requirement, not an option.** A new feature does not send location or trip data to a server unless the
  user reports something themselves.
- Calm UI: nothing that flashes or pops up unless it is needed for safety.

## Submitting a change
1. Fork, create a branch, keep the PR small (one topic).
2. Describe what you tested: device/OS and (for the DASH01) whether you tried it on a real device.
3. Server: the code in `server/app/` runs with `docker compose up -d --build`.

## Licence
By contributing you agree that your contribution falls under the **GPLv3**.

## Questions
Ask them in **GitHub Discussions**. Do not report security issues in a public issue, but privately to the maintainer (see the GitHub profile).
