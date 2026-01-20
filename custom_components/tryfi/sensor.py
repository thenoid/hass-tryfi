"""Platform for sensor integration."""
import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    STATE_OK,
    STATE_PROBLEM,
    UnitOfLength,
    UnitOfTime
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, SENSOR_STATS_BY_TIME, SENSOR_STATS_BY_TYPE

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        pet_name = getattr(pet, "name", "unknown")
        pet_id = getattr(pet, "petId", "unknown")
        LOGGER.debug(
            "Adding Pet Battery Sensor for %s (%s)",
            pet_name,
            pet_id,
        )
        new_devices.append(TryFiBatterySensor(hass, pet, coordinator))
        for statType in SENSOR_STATS_BY_TYPE:
            for statTime in SENSOR_STATS_BY_TIME:
                LOGGER.debug(
                    "Adding Pet Stat for %s (%s) [%s/%s]",
                    pet_name,
                    pet_id,
                    statType,
                    statTime,
                )
                new_devices.append(
                    PetStatsSensor(hass, pet, coordinator, statType, statTime)
                )
        LOGGER.debug(
            "Adding Pet Generic Sensor for %s (%s)",
            pet_name,
            pet_id,
        )
        new_devices.append(PetGenericSensor(hass, pet, coordinator, "Activity Type"))
        new_devices.append(PetGenericSensor(hass, pet, coordinator, "Current Place Name"))
        new_devices.append(PetGenericSensor(hass, pet, coordinator, "Current Place Address"))
        new_devices.append(PetGenericSensor(hass, pet, coordinator, "Connected To"))
        

    for base in tryfi.bases:
        base_name = getattr(base, "name", "unknown")
        base_id = getattr(base, "baseId", "unknown")
        LOGGER.debug("Adding Base %s (%s)", base_name, base_id)
        new_devices.append(TryFiBaseSensor(hass, base, coordinator))
    if new_devices:
        async_add_devices(new_devices)


class TryFiBaseSensor(CoordinatorEntity, Entity):
    def __init__(self, hass, base, coordinator):
        self._hass = hass
        self._baseId = base.baseId
        self._online = base.online
        self._base = base
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        base = self.base
        base_name = getattr(base, "name", "Unknown")
        return f"{base_name}"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        base = self.base
        base_id = getattr(base, "baseId", self._baseId)
        return f"{base_id}"

    @property
    def baseId(self):
        return self._baseId

    @property
    def base(self):
        return self.coordinator.data.getBase(self.baseId)

    @property
    def device_id(self):
        return self.unique_id

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return None

    @property
    def state(self):
        base = self.base
        if getattr(base, "online", False):
            return "Online"
        return "Offline"

    @property
    def icon(self):
        return "mdi:wifi"

    @property
    def device_info(self):
        base = self.base
        return {
            "identifiers": {(DOMAIN, getattr(base, "baseId", self._baseId))},
            "name": getattr(base, "name", "Unknown"),
            "manufacturer": "TryFi",
            "model": "TryFi Base",
            # "sw_version": self.pet.device.buildId,
        }

class PetGenericSensor(CoordinatorEntity, Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, pet, coordinator, statType):
        self._hass = hass
        self._petId = pet.petId
        self._statType = statType
        super().__init__(coordinator)
    
    @property
    def statType(self):
        return self._statType

    @property
    def statTime(self):
        return self._statTime

    @property
    def name(self):
        """Return the name of the sensor."""
        pet = self.pet
        pet_name = getattr(pet, "name", "Unknown")
        return f"{pet_name} {self.statType.title()}"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        formattedType = self.statType.lower().replace(" ", "-")
        pet = self.pet
        pet_id = getattr(pet, "petId", self._petId)
        return f"{pet_id}-{formattedType}"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def device(self):
        return getattr(self.pet, "device", None)

    @property
    def device_id(self):
        return self.unique_id

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return None

    @property
    def icon(self):
        if self.statType == "Activity Type":
            return "mdi:run"
        elif self.statType == "Current Place Name":
            return "mdi:earth"
        elif self.statType == "Current Place Address":
            return "mdi:map-marker"
        elif self.statType == "Connected To":
            return "mdi:human-greeting-proximity"

    @property
    def state(self):
        pet = self.pet
        if pet is None:
            return None
        if self.statType == "Activity Type":
            return pet.getActivityType()
        elif self.statType == "Current Place Name":
            return pet.getCurrPlaceName()
        elif self.statType == "Current Place Address":
            return pet.getCurrPlaceAddress()
        elif self.statType == "Connected To":
            device = getattr(pet, "device", None)
            if device is None:
                return None
            try:
                return device.connectionStateType
            except AttributeError:
                return None
    @property
    def unit_of_measurement(self):
        return None

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

class PetStatsSensor(CoordinatorEntity, Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, pet, coordinator, statType, statTime):
        self._hass = hass
        self._petId = pet.petId
        self._statType = statType
        self._statTime = statTime
        super().__init__(coordinator)

    @property
    def statType(self):
        return self._statType

    @property
    def statTime(self):
        return self._statTime

    @property
    def name(self):
        """Return the name of the sensor."""
        pet = self.pet
        pet_name = getattr(pet, "name", "Unknown")
        return f"{pet_name} {self.statTime.title()} {self.statType.title()}"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        pet = self.pet
        pet_id = getattr(pet, "petId", self._petId)
        return f"{pet_id}-{self.statTime.lower()}-{self.statType.lower()}"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def device(self):
        return getattr(self.pet, "device", None)

    @property
    def device_id(self):
        return self.unique_id

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return None

    @property
    def icon(self):
        return "mdi:map-marker-distance"

    @property
    def state(self):
        pet = self.pet
        if pet is None:
            return None
        if self.statType.upper() == "STEPS":
            if self.statTime.upper() == "DAILY":
                return getattr(pet, "dailySteps", None)
            elif self.statTime.upper() == "WEEKLY":
                return getattr(pet, "weeklySteps", None)
            elif self.statTime.upper() == "MONTHLY":
                return getattr(pet, "monthlySteps", None)
        elif self.statType.upper() == "DISTANCE":
            if self.statTime.upper() == "DAILY":
                distance = getattr(pet, "dailyTotalDistance", None)
                if distance is None:
                    return None
                return round(distance / 1000, 2)
            elif self.statTime.upper() == "WEEKLY":
                distance = getattr(pet, "weeklyTotalDistance", None)
                if distance is None:
                    return None
                return round(distance / 1000, 2)
            elif self.statTime.upper() == "MONTHLY":
                distance = getattr(pet, "monthlyTotalDistance", None)
                if distance is None:
                    return None
                return round(distance / 1000, 2)
        elif self.statType.upper() == "NAP":
            if self.statTime.upper() == "DAILY":
                nap = getattr(pet, "dailyNap", None)
                if nap is None:
                    return None
                return round(nap / 60, 2)
            elif self.statTime.upper() == "WEEKLY":
                nap = getattr(pet, "weeklyNap", None)
                if nap is None:
                    return None
                return round(nap / 60, 2)
            elif self.statTime.upper() == "MONTHLY":
                nap = getattr(pet, "monthlyNap", None)
                if nap is None:
                    return None
                return round(nap / 60, 2)
        elif self.statType.upper() == "SLEEP":
            if self.statTime.upper() == "DAILY":
                sleep = getattr(pet, "dailySleep", None)
                if sleep is None:
                    return None
                return round(sleep / 60, 2)
            elif self.statTime.upper() == "WEEKLY":
                sleep = getattr(pet, "weeklySleep", None)
                if sleep is None:
                    return None
                return round(sleep / 60, 2)
            elif self.statTime.upper() == "MONTHLY":
                sleep = getattr(pet, "monthlySleep", None)
                if sleep is None:
                    return None
                return round(sleep / 60, 2)
        else:
            return None

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        if self.statType.upper() == "DISTANCE":
            return UnitOfLength.KILOMETERS
        elif self.statType.upper() == "SLEEP":
            return UnitOfTime.MINUTES
        elif self.statType.upper() == "NAP":
            return UnitOfTime.MINUTES
        else:
            return "steps"

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


class TryFiBatterySensor(CoordinatorEntity, Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, pet, coordinator):
        self._hass = hass
        self._petId = pet.petId
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        pet = self.pet
        pet_name = getattr(pet, "name", "Unknown")
        return f"{pet_name} Collar Battery Level"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        pet = self.pet
        pet_id = getattr(pet, "petId", self._petId)
        return f"{pet_id}-battery"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def device(self):
        return getattr(self.pet, "device", None)

    @property
    def device_id(self):
        return self.unique_id

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.BATTERY

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return PERCENTAGE

    @property
    def isCharging(self):
        pet = self.pet
        device = getattr(pet, "device", None)
        return bool(getattr(device, "isCharging", False))

    @property
    def icon(self):
        """Return the icon for the battery."""
        return icon_for_battery_level(
            battery_level=self.batteryPercent, charging=self.isCharging
        )

    @property
    def batteryPercent(self):
        """Return the state of the sensor."""
        pet = self.pet
        device = getattr(pet, "device", None)
        return getattr(device, "batteryPercent", None)

    @property
    def state(self):
        return self.batteryPercent

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
