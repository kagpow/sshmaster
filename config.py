import configparser
import json
from dataclasses import dataclass
from typing import Any

CONFIG_FILE = 'data/config.ini'


@dataclass
class ConfigItem:
    section: str
    name: str
    full_name: str
    value: Any
    description: str
    need_restart: bool = False


DEFAULT_CONFIG = [
    ConfigItem(
        'SSH', 'tasks_count', 'ssh_tasks_count', 50,
        "Số thread check fresh SSH"),
    ConfigItem(
        'SSH', 'auto_delete_died', 'ssh_auto_delete_died', False,
        "Tự động xoá SSH die"
    ),
    ConfigItem(
        'SSH', 'test_timeout', 'ssh_test_timeout', 60,
        "Số giây check live SSH tối đa (từ kết nối đến test IP)"
    ),
    ConfigItem(
        'PORT', 'auto_replace_died_ssh', 'port_auto_replace_died_ssh', True,
        "Tự động thay thế SSH die"
    ),
    ConfigItem(
        'PORT', 'use_unique_ssh', 'use_unique_ssh', False,
        "Không dùng lại các SSH đã dùng ở mỗi Port"
    ),
    ConfigItem(
        'PORT', 'auto_reset_ports', 'auto_reset_ports', False,
        "Tự động đổi IP mỗi Port sau một thời gian nhất định"),
    ConfigItem(
        'PORT', 'reset_interval', 'port_reset_interval', 60,
        "Thời gian reset IP từng port (đổi IP mỗi x giây)"),
    ConfigItem(
        'WEB', 'port', 'web_port', 6080,
        "Port chạy web (truy cập web bằng link http://<ip>:<port>)",
        need_restart=True),
    ConfigItem(
        'SSHSTORE', 'enabled', 'sshstore_enabled', False,
        "Tự động lấy SSH từ SSHStore (cần tạo account)"
    ),
    ConfigItem(
        'SSHSTORE', 'api_key', 'sshstore_api_key', '',
        "API key của SSHStore"
    ),
    ConfigItem(
        'SSHSTORE', 'country', 'sshstore_country', 'All',
        "Quốc gia lấy SSH từ SSHSTORE"
    ),
]

PYDANTIC_ARGS = {}
for i in DEFAULT_CONFIG:
    PYDANTIC_ARGS[i.full_name] = (type(i.value), i.value)


def get_default_config():
    config = configparser.ConfigParser()
    for item in DEFAULT_CONFIG:
        if item.section not in config.sections():
            config.add_section(item.section)
        config[item.section][item.name] = json.dumps(item.value)
    return config


def get_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if not config.sections():
        config = get_default_config()
        write_config(config)
    return config


def get(full_name: str):
    for item in DEFAULT_CONFIG:
        if item.full_name == full_name:
            return get_by_item(item)
    raise RuntimeError(f"Config {repr(full_name)} not found")


def get_by_item(item: ConfigItem):
    config = get_config()
    value = config.get(item.section, item.name)
    return json.loads(value)


def write_config(config):
    with open(CONFIG_FILE, 'w+') as file:
        config.write(file)


def reset_config():
    write_config(get_default_config())
