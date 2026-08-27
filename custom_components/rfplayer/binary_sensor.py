# Modified for the JAM'ALERT Community patch: reliable RFPlayer JAMMING diagnostics and state handling.
"""Support for RfPlayer binary sensors."""

import logging

from custom_components.rfplayer.const import COMMAND_GROUP_LIST, COMMAND_OFF_LIST, COMMAND_ON_LIST
from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpPlatformConfig, RfpSensorConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig,
) -> BinarySensorEntityDescription:
    return BinarySensorEntityDescription(
        key=config.name,
        device_class=BinarySensorDeviceClass(config.device_class) if config.device_class else None,
        entity_category=config.category,
    )


def _builder(
    device: RfDeviceId,
    platform_configs: list[AnyRfpPlatformConfig],
    event_data: RfPlayerEventData | None,
    verbose: bool,
) -> list[Entity]:
    return [
        RfPlayerBinarySensor(device, _get_entity_description(config), config, event_data=event_data, verbose=verbose)
        for config in platform_configs
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up config rf device entry."""

    await async_setup_platform_entry(
        hass,
        config_entry,
        async_add_entities,
        Platform.BINARY_SENSOR,
        _builder,
    )


class RfPlayerBinarySensor(RfDeviceEntity, BinarySensorEntity):
    """A representation of a RfPlayer binary sensor."""

    _attr_force_update = True
    _attr_name = None

    def __init__(
        self,
        device: RfDeviceId,
        entity_description: BinarySensorEntityDescription,
        platform_config: RfpPlatformConfig,
        event_data: RfPlayerEventData | None,
        verbose: bool,
    ) -> None:
        """Initialize the RfPlayer sensor."""
        super().__init__(device_id=device, profile_name=platform_config.name, event_data=event_data, verbose=verbose)

        # JAM'ALERT v2: old RFPlayer builds may have left a stale entity
        # registered with unique_id ``jamming_0_detector``. Reusing that ID
        # makes Home Assistant ignore the fresh entity even though live
        # JAMMING frames are received correctly. Give JAM'ALERT a dedicated
        # identity so the live detector can be created immediately.
        if device.protocol.upper() == "JAMMING":
            self._attr_unique_id = "rfplayer_jamalert_detector_v2"
            self.entity_id = "binary_sensor.rfplayer_jamalert_detector"

        self.entity_description = entity_description
        assert isinstance(platform_config, RfpSensorConfig)
        self._config = platform_config
        self._event_data = event_data

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        state = self._config.state.get_value(event_data)
        command = state.lower().strip() if state is not None else None

        # JAM'ALERT firmware frames are not fully documented across all
        # RFP1000 revisions. Accept the standard binary values first, then
        # common textual meanings if the firmware provides subTypeMeaning.
        if self._device_id.protocol == "JAMMING":
            infos = event_data.get("frame", {}).get("infos", {})
            meaning = str(infos.get("subTypeMeaning", "")).lower().strip()
            if command in COMMAND_ON_LIST or meaning in {"jamming", "jam", "alert", "alarm", "detected", "on", "true"}:
                self._attr_is_on = True
            elif command in COMMAND_OFF_LIST or meaning in {"normal", "clear", "off", "false", "no jamming", "no_jamming"}:
                self._attr_is_on = False
            else:
                _LOGGER.warning(
                    "RFPLAYER JAMMING state not understood: subType=%s subTypeMeaning=%s",
                    state,
                    infos.get("subTypeMeaning"),
                )
                return False
            _LOGGER.warning(
                "RFPLAYER JAM'ALERT STATE: %s (subType=%s subTypeMeaning=%s)",
                "DETECTED" if self._attr_is_on else "CLEAR",
                state,
                infos.get("subTypeMeaning"),
            )
        elif command in COMMAND_ON_LIST:
            self._attr_is_on = True
        elif command in COMMAND_OFF_LIST:
            self._attr_is_on = False
        else:
            _LOGGER.info("Unsupported binary sensor command %s", command)
            return False

        return True

    def _group_event(self, event: RfDeviceEvent) -> bool:
        value = self._config.state.get_value(event.data)
        return value.lower() in COMMAND_GROUP_LIST if value else False
