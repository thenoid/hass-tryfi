from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiLostMode(hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices)


class TryFiLostMode(CoordinatorEntity, SelectEntity):
    def __init__(self, hass, pet, coordinator):
        self._petId = pet.petId
        self._hass = hass
        super().__init__(coordinator)

    @property
    def name(self):
        pet = self.pet
        pet_name = getattr(pet, "name", "Unknown")
        return f"{pet_name} Lost Mode"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def tryfi(self):
        return self.coordinator.data

    @property
    def unique_id(self):
        pet = self.pet
        pet_id = getattr(pet, "petId", self._petId)
        return f"{pet_id}-lost"

    @property
    def device_id(self):
        return self.unique_id

    @property
    def options(self):
        return ['Safe', 'Lost']

    @property
    def current_option(self):
        device = getattr(self.pet, "device", None)
        if device is None:
            return 'Safe'
        try:
            return 'Lost' if device.isLost else 'Safe'
        except AttributeError:
            return 'Safe'

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
    
    def select_option(self, option):
        self.pet.setLostDogMode(self.tryfi.session, option == 'Lost')
