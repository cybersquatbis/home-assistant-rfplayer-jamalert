# GCE RF Player JAM'ALERT Community

Community maintenance patch for the Home Assistant **GCE RF Player** custom integration, focused on restoring reliable **JAM'ALERT / RF jamming detection** on RFPlayer/RFP1000 hardware.

This is a derivative of the upstream GCE Electronics integration. It is **not an official GCE Electronics release**. The upstream project remains the source for the base integration and protocol support.

## What this community build fixes

- Handles `JAMMING` packets even when they do not contain a normal RF device address.
- Maps receiver-level JAMMING packets to the stable diagnostic device `JAMMING_0`.
- Creates a dedicated live detector entity to avoid stale Home Assistant entity-registry collisions.
- Decodes JAMMING state from both `subType` and `subTypeMeaning`.
- Adds useful diagnostics for connection, raw RX packets and JAMMING events.
- Protects the serial event callback from malformed/unsupported packets.
- Fixes the `all_off` state-list typo from the base 1.5.0 code.

## Expected JAM'ALERT entity

After the integration receives a JAMMING frame, the community build exposes the live detector as:

```text
binary_sensor.rfplayer_jamalert_detector
```

Typical states:

- `off`: no jamming currently reported by RFPlayer;
- `on`: jamming reported by RFPlayer;
- `unavailable`: RFPlayer/integration is not available.

Do **not** treat `unknown` as a safe/normal RF state.

## Recommended RFPlayer configuration

In the RFPlayer integration options, enable the receiver protocol **JAMMING** and configure an initialization command such as:

```text
JAMMING 7
```

A threshold around 7 is a practical starting point. Tune it for the local RF environment and verify false positives before using the signal for security automations.

For diagnostics, enable verbose mode temporarily and optionally add:

```yaml
logger:
  default: info
  logs:
    custom_components.rfplayer: debug
```

Then search Home Assistant logs for `RFPLAYER` or `JAMMING`.

## Installation

### Manual

1. Remove or back up any existing `/config/custom_components/rfplayer/` folder.
2. Copy `custom_components/rfplayer/` from this repository to `/config/custom_components/rfplayer/`.
3. Restart Home Assistant.
4. Reconfigure the RFPlayer serial port using its persistent `/dev/serial/by-id/...` path.
5. Enable JAMMING reception and configure the JAMMING initialization command if desired.

### HACS custom repository

Add this repository URL in HACS as a custom **Integration** repository, install it, then restart Home Assistant.

## Compatibility and migration

This package uses the same Home Assistant domain, `rfplayer`, as the upstream integration. It is a drop-in replacement, **not a second integration that can run beside the upstream build**.

Older installations may contain a stale entity such as:

```text
binary_sensor.jamming_0_detector
```

The community build intentionally uses the dedicated live entity:

```text
binary_sensor.rfplayer_jamalert_detector
```

The stale legacy entity can be ignored or removed from the entity registry once the live detector is confirmed working.

## Security note

JAM'ALERT is a radio-interference/jamming indicator, not a certified anti-intrusion system. Avoid automatically sounding a siren from a single transient RF event. A confirmation delay and independent alarm sensors are recommended.

Do not intentionally operate illegal radio-jamming equipment to test this feature.

## Privacy

This Community package contains no installation-specific Home Assistant entity IDs, personal names, notification targets, local IP addresses, USB serial identifiers, tokens or private configuration.

## Attribution and license

**The original RFPlayer integration and the core work are from GCE Electronics.** This repository only provides community modifications and maintenance needed for our Home Assistant use case, especially JAM'ALERT handling on recent installations.

Upstream GCE Electronics project:
https://github.com/gce-electronics/HA_RFPlayer

Distributed under the **Apache License 2.0**. See `LICENSE` and `NOTICE`.
