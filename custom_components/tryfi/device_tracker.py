import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.const import (
    PERCENTAGE,
    STATE_OK,
    STATE_PROBLEM,
    UnitOfLength,
    UnitOfTime
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiPetTracker(async_add_devices, hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices, True)


class TryFiPetTracker(CoordinatorEntity, TrackerEntity):
    def __init__(self, see, hass, pet, coordinator):
        self._petId = pet.petId
        self._see = see
        super().__init__(coordinator)

    @property
    def name(self):
        pet = self.pet
        pet_name = getattr(pet, "name", "Unknown")
        return f"{pet_name} Tracker"

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def petId(self):
        return self._petId

    @property
    def unique_id(self):
        pet = self.pet
        pet_id = getattr(pet, "petId", self._petId)
        return f"{pet_id}-tracker"

    @property
    def device_id(self):
        return self.unique_id

    @property
    def entity_picture(self):
        return getattr(self.pet, "photoLink", None)

    @property
    def latitude(self):
        latitude = getattr(self.pet, "currLatitude", None)
        if latitude is None:
            return None
        return float(latitude)

    @property
    def longitude(self):
        longitude = getattr(self.pet, "currLongitude", None)
        if longitude is None:
            return None
        return float(longitude)

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def battery_level(self):
        device = getattr(self.pet, "device", None)
        return getattr(device, "batteryPercent", None)

    @property
    def device_info(self):
        pet = self.pet
        device = getattr(pet, "device", None)
        return {
            "identifiers": {(DOMAIN, getattr(pet, "petId", self._petId))},
            "name": getattr(pet, "name", "Unknown"),
            "manufacturer": "TryFi",
            "model": getattr(pet, "breed", None),
            "sw_version": getattr(device, "buildId", None),
        }
