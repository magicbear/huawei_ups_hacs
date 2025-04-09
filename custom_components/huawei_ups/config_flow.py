# config_flow.py
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SLAVE_ID, CONF_HOST, CONF_PORT, CONF_SLAVE_ID, DEFAULT_SCAN_INTERVAL

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int
})

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    client = AsyncModbusTcpClient(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        timeout=5
    )

    try:
        # 测试读取第一个状态寄存器（地址40001对应modbus地址0）
        await client.connect()
        if not client.connected:
            raise ConnectionError("Modbus connection failed")

        result = await client.read_holding_registers(
            address=0,
            count=1,
            slave=data[CONF_SLAVE_ID]
        )

        if result.isError():
            raise ModbusException("Modbus error: {}".format(result))

        # client.close()
        # 成功读取至少一个寄存器值
        return {"title": "Huawei UPS"}

    except ModbusException as e:
        client.close()
        raise ValueError("modbus_communication_error") from e


@config_entries.HANDLERS.register(DOMAIN)
class HuaweiUPSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Huawei UPS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = {"title": "Huawei UPS"}

                # 检查是否已配置
                # await self.async_set_unique_id(user_input[CONF_HOST])
                # self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

            except ConnectionError:
                errors["base"] = "cannot_connect"
            except ValueError as e:
                if str(e) == "modbus_communication_error":
                    errors["base"] = "modbus_error"
                else:
                    errors["base"] = "unknown"
                    _LOGGER.error("Unexcepted error %s: %s", e.__class__.__name__, e)
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.error("Unexcepted error %s: %s", e.__class__.__name__, e)
                errors["base"] = "unknown"

            print(errors)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )
