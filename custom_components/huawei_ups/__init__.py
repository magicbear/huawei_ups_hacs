
import asyncio
import json
import logging

from homeassistant.config_entries import ConfigEntry, CONN_CLASS_CLOUD_PUSH, CONN_CLASS_LOCAL_PUSH
from homeassistant.const import (
    CONF_URL,
    CONF_TYPE,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    EVENT_HOMEASSISTANT_STOP,
    SERVICE_RELOAD,
    Platform,
)
from homeassistant.core import HomeAssistant, Event, ServiceCall
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity import Entity
from .sensor import HuaweiUPSDataCoordinator, HuaweiUPSSensor
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, Platform.SENSOR)
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR]
    )
    return unload_ok