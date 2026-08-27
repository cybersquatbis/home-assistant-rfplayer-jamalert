# Changelog

## 1.5.0-jamalert.2 Community

- Confirmed live decoding of RFPlayer `JAMMING` frames (`infoType: 1`).
- Added stable synthetic address handling for receiver-level JAMMING frames.
- Added dedicated `binary_sensor.rfplayer_jamalert_detector` identity to avoid stale entity collisions.
- Added tolerant JAMMING ON/OFF decoding.
- Added connection, raw RX, event and JAMMING diagnostics.
- Protected serial callbacks from malformed event packets.
- Fixed `all_off` typo in RFPlayer command state lists.
- Removed all installation-specific data from the Community distribution.
