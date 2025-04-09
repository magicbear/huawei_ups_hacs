# sensor.py
import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Endian
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SLAVE_ID, CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = [
    ("Input Voltage A", "UinA", "V", SensorDeviceClass.VOLTAGE),
    ("Input Voltage B", "UinB", "V", SensorDeviceClass.VOLTAGE),
    ("Input Voltage C", "UinC", "V", SensorDeviceClass.VOLTAGE),
    ("Input Voltage AB", "UinAB", "V", SensorDeviceClass.VOLTAGE),
    ("Input Voltage BC", "UinBC", "V", SensorDeviceClass.VOLTAGE),
    ("Input Voltage CA", "UinCA", "V", SensorDeviceClass.VOLTAGE),
    ("Input Current A", "IinA", "A", SensorDeviceClass.CURRENT),
    ("Input Current B", "IinB", "A", SensorDeviceClass.CURRENT),
    ("Input Current C", "IinC", "A", SensorDeviceClass.CURRENT),
    ("Input Current N", "IZeroSeq", "A", SensorDeviceClass.CURRENT),
    ("Input Power Factor A", "PFinA", "%", SensorDeviceClass.POWER_FACTOR),
    ("Input Power Factor B", "PFinB", "%", SensorDeviceClass.POWER_FACTOR),
    ("Input Power Factor C", "PFinC", "%", SensorDeviceClass.POWER_FACTOR),

    ("Output Voltage A", "UoutA", "V", SensorDeviceClass.VOLTAGE),
    ("Output Voltage B", "UoutB", "V", SensorDeviceClass.VOLTAGE),
    ("Output Voltage C", "UoutC", "V", SensorDeviceClass.VOLTAGE),
    ("Output Voltage AB", "UoutAB", "V", SensorDeviceClass.VOLTAGE),
    ("Output Voltage BC", "UoutBC", "V", SensorDeviceClass.VOLTAGE),
    ("Output Voltage CA", "UoutCA", "V", SensorDeviceClass.VOLTAGE),
    ("Output Current A", "IoutA", "A", SensorDeviceClass.CURRENT),
    ("Output Current B", "IoutB", "A", SensorDeviceClass.CURRENT),
    ("Output Current C", "IoutC", "A", SensorDeviceClass.CURRENT),
    ("Output Power Factor A", "PFoutA", "%", SensorDeviceClass.POWER_FACTOR),
    ("Output Power Factor B", "PFoutB", "%", SensorDeviceClass.POWER_FACTOR),
    ("Output Power Factor C", "PFoutC", "%", SensorDeviceClass.POWER_FACTOR),
    ("Output Load A", "LoadA", "%", SensorDeviceClass.BATTERY),
    ("Output Load B", "LoadB", "%", SensorDeviceClass.BATTERY),
    ("Output Load C", "LoadC", "%", SensorDeviceClass.BATTERY),
    # ("Output Active Power A", "PactiveA", "W", SensorDeviceClass.POWER),
    # ("Output Active Power B", "PactiveB", "W", SensorDeviceClass.POWER),
    # ("Output Active Power C", "PactiveC", "W", SensorDeviceClass.POWER),
    # ("Output Real Power A", "PrealA", "W", SensorDeviceClass.POWER),
    # ("Output Real Power B", "PrealB", "W", SensorDeviceClass.POWER),
    # ("Output Real Power C", "PrealC", "W", SensorDeviceClass.POWER),
    # ("Output VAR Power A", "PvarA", "W", SensorDeviceClass.POWER),
    # ("Output VAR Power B", "PvarB", "W", SensorDeviceClass.POWER),
    # ("Output VAR Power C", "PvarC", "W", SensorDeviceClass.POWER),
    # ("Output Peak Power A", "PeakA", "W", SensorDeviceClass.POWER),
    # ("Output Peak Power B", "PeakB", "W", SensorDeviceClass.POWER),
    # ("Output Peak Power C", "PeakC", "W", SensorDeviceClass.POWER),

    ("Battery Voltage +", "VbatPos", "V", SensorDeviceClass.VOLTAGE),
    ("Battery Voltage -", "VbatNeg", "V", SensorDeviceClass.VOLTAGE),
    ("Temperature", "Temp", "°C", SensorDeviceClass.TEMPERATURE),

    ("Input Frequency", "Fin", "Hz", SensorDeviceClass.FREQUENCY),
    ("Output Frequency", "Fout", "Hz", SensorDeviceClass.FREQUENCY),
    # 添加所有需要监控的传感器字段
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = HuaweiUPSDataCoordinator(hass, config_entry)

    # 确保协调器已初始化
    await coordinator.async_config_entry_first_refresh()

    # 确保update_interval类型正确
    if not isinstance(coordinator.update_interval, timedelta):
        raise ValueError("Invalid update interval type")

    sensors = []
    for name, key, unit, device_class in SENSOR_TYPES:
        sensors.append(
            HuaweiUPSSensor(coordinator, name, key, unit, device_class)
        )

    async_add_entities(sensors)


class HuaweiUPSSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name, key, unit, device_class):
        super().__init__(coordinator, key)
        self._attr_device_info = coordinator.device_info
        self.entity_description = SensorEntityDescription(
            key=key,
            name=name,
            device_class=device_class,
            native_unit_of_measurement=unit,
            has_entity_name=True,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """处理来自协调器的更新数据。"""
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def unique_id(self):
        return f"{self.entity_description.key.lower()}"


class HuaweiUPSDataCoordinator(DataUpdateCoordinator):
    """异步数据协调器"""

    def __init__(self, hass, config_entry):
        host, port, slave_id = config_entry.data[CONF_HOST], config_entry.data[CONF_PORT], config_entry.data[CONF_SLAVE_ID]
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Huawei UPS",
            update_interval=timedelta(seconds=config_entry.data[CONF_SCAN_INTERVAL]),
        )
        self.client = AsyncModbusTcpClient(
            host=host,
            port=port,
            timeout=10
        )
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name= "Huawei UPS",
            manufacturer="Huawei",
            model="HUAWEI_UPS"
        )
        self.slave_id = slave_id
        self.data = {}

    async def _async_update_data(self):
        """异步获取所有数据"""
        try:
            # 连接检查
            if not self.client.connected:
                await self.client.connect()

            if not self.client.connected:
                raise Exception("Connection lost")

            # 读取Alert (40301)
            result = await self.client.read_holding_registers(address=300, count=1, slave=self.slave_id)

            if result.isError():
                self.logger.error("Status register read error: %s", result)
                return None

            alert_word = self.client.convert_from_registers(result.registers, data_type=self.client.DATATYPE.UINT16, word_order=Endian.BIG)

            # 读取系统状态寄存器 (40131)
            result = await self.client.read_holding_registers(
                address=130,
                count=1,
                slave=self.slave_id
            )

            if result.isError():
                self.logger.error("Status register read error: %s", result)
                return None

            status_word = self.client.convert_from_registers(result.registers, data_type=self.client.DATATYPE.UINT16, word_order=Endian.BIG)

            # 读取输入参数 (40001)
            input_result = await self.client.read_holding_registers(
                address=0,
                count=17,
                slave=self.slave_id
            )

            if input_result.isError():
                self.logger.error("Input register read error: %s", input_result)
                return None

            input_decoder = self.client.convert_from_registers(
                input_result.registers,
                data_type=self.client.DATATYPE.INT16,
                word_order=Endian.BIG
            )

            # 读取输出参数 (40046)
            output_result = await self.client.read_holding_registers(
                address=45,  # 40046 - 40001 = 45
                count=28,
                slave=self.slave_id
            )

            if output_result.isError():
                self.logger.error("Input register read error: %s", output_result)
                return None

            output_decoder = self.client.convert_from_registers(
                output_result.registers,
                data_type=self.client.DATATYPE.INT16,
                word_order=Endian.BIG
            )

            # 构造完整数据集
            self.data = {
                'Alert': alert_word,
                # 系统状态
                #   0 均不供电
                #   1 旁路
                #   2 主路逆变
                #   3 电池逆变
                #   4 联合
                #   5 市电ECO
                #   6 电池ECO
                'PowerState': (status_word >> 7) & 0x7,
                #   0 单机
                #   1 并机
                #   2 单机ECO
                #   3 并机ECO
                #   4 老化
                #   5 变频器
                #   6 单机智能在线
                'UPSRunState': (status_word >> 10) & 0x7,
                #   0 未接入
                #   1 非充非放
                #   2 休眠
                #   3 浮充
                #   4 均充
                #   5 放电
                'BatteryState': (status_word >> 13) & 0x7,

                # 输入参数
                'UinA': input_decoder[0] / 10.,
                'UinB': input_decoder[1] / 10.,
                'UinC': input_decoder[2] / 10.,
                'UinAB': input_decoder[3] / 10.,
                'UinBC': input_decoder[4] / 10.,
                'UinCA': input_decoder[5] / 10.,
                'IinA': input_decoder[6] / 10.,
                'IinB': input_decoder[7] / 10.,
                'IinC': input_decoder[8] / 10.,
                'Fin':  input_decoder[9] / 100.,
                'PFinA': input_decoder[10] / 100.,
                'PFinB': input_decoder[11] / 100.,
                'PFinC': input_decoder[12] / 100.,
                'VbatPos': input_decoder[13] / 10.,
                'VbatNeg': input_decoder[14] / 10.,
                'IZeroSeq': input_decoder[15] / 10.,
                'Temp': input_decoder[16] / 10.,

                # 输出参数
                'UoutA': output_decoder[0] / 10.,
                'UoutB': output_decoder[1] / 10.,
                'UoutC': output_decoder[2] / 10.,
                'UoutAB': output_decoder[3] / 10.,
                'UoutBC': output_decoder[4] / 10.,
                'UoutCA': output_decoder[5] / 10.,
                'IoutA': output_decoder[6] / 10.,
                'IoutB': output_decoder[7] / 10.,
                'IoutC': output_decoder[8] / 10.,
                'Fout': output_decoder[9] / 100.,
                # 'PactiveA': output_decoder[10] / 10.,
                # 'PactiveB': output_decoder[11] / 10.,
                # 'PactiveC': output_decoder[12] / 10.,
                # 'PrealA': output_decoder[13] / 10.,
                # 'PrealB': output_decoder[14] / 10.,
                # 'PrealC': output_decoder[15] / 10.,
                # 'PvarA': output_decoder[16] / 10.,
                # 'PvarB': output_decoder[17] / 10.,
                # 'PvarC': output_decoder[18] / 10.,
                'PFoutA': output_decoder[19] / 100.,
                'PFoutB': output_decoder[20] / 100.,
                'PFoutC': output_decoder[21] / 100.,
                'LoadA': output_decoder[22] / 10.,
                'LoadB': output_decoder[23] / 10.,
                'LoadC': output_decoder[24] / 10.,
                # 'PeakA': output_decoder[25] / 10.,
                # 'PeakB': output_decoder[26] / 10.,
                # 'PeakC': output_decoder[27] / 10.,
            }

            self.client.close()
            return self.data
        except Exception as e:
            self.logger.error("Update failed: %s", str(e))
            self.client.close()
            raise

