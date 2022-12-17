import asyncio
import typing
from datetime import datetime

from pony.orm import Optional, Required, Set, composite_key

import utils
from models import db
from models.common import auto_renew_objects


class Model(db.Entity):
    last_checked = Optional(datetime)
    last_modified = Required(datetime, default=datetime.now)

    def before_update(self):
        self.last_modified = datetime.now()

    @auto_renew_objects
    def _update_check_result(self, **kwargs):
        self.set(**kwargs, last_checked=datetime.now())

    async def update_check_result(self, **kwargs):
        return await asyncio.to_thread(self._update_check_result, **kwargs)

    @auto_renew_objects
    def reset_status(self):
        """
        Reset all object's status.
        """
        self.last_checked = None

    @auto_renew_objects
    def load(self):
        super().load()
        return self


class SSH(Model):
    """
    Store SSH information.
    """
    ip = Required(str)
    username = Optional(str)
    password = Optional(str)
    ssh_port = Required(int, default=22)
    is_live = Optional(bool)

    composite_key(ip, ssh_port, username, password)

    port = Optional('Port')
    used_ports: Set = Set('Port')

    def before_update(self):
        super().before_update()

        # Update used ports
        if self.port is not None and self.port not in self.used_ports:
            self.used_ports.add(self.port)

    @classmethod
    @auto_renew_objects
    def get_ssh_for_port(cls, port: 'Port', unique=True):
        """
        Get _run_with_reset_is_working usable SSH for provided Port. Will not get one that was used by
        that Port before if unique=True.

        :param port: Port
        :param unique: True if the SSH cannot be used before by Port
        :return: Usable SSH for Port
        """
        query = cls.select(lambda s: s.is_live)
        if unique:
            query = query.filter(lambda s: s.id not in port.used_ssh_list.id)

        if result := query.random(1):
            return result[0]
        else:
            return None

    @auto_renew_objects
    def delete_if_died(self):
        """
        Delete the SSH if it is died.

        :return: Whether the SSH is deleted or not.
        """
        if not self.is_live:
            self.delete()
            return True
        else:
            return False


class Port(Model):
    """
    Store port information.
    """
    port_number = Required(int, unique=True, min=1024, max=65353)
    auto_connect = Required(bool, default=True)

    ssh = Optional(SSH)
    is_connected = Required(bool, default=False)
    public_ip = Optional(str)  # Proxy's public IP

    time_connected = Optional(datetime)
    is_working = Required(bool, default=False)
    used_ssh_list: Set = Set(SSH, reverse='used_ports')
    proxy_address = Optional(str)

    def before_update(self):
        super().before_update()

        # Update time connected
        if self.is_connected:
            self.time_connected = self.time_connected or datetime.now()
        else:
            self.time_connected = None

        # Update used SSH
        if self.is_connected:
            if self.ssh is not None and self.ssh not in self.used_ssh_list:
                self.used_ssh_list.add(self.ssh)

        self.proxy_address = f"socks5://{utils.get_ipv4_address()}:{self.port_number}"

    @auto_renew_objects
    def need_reset(self, time_expired: datetime):
        return self.time_connected is not None and self.time_connected < time_expired

    @property
    @auto_renew_objects
    def need_ssh(self):
        return self.ssh is None

    @auto_renew_objects
    def assign_ssh(self, ssh: typing.Optional[SSH]):
        self.ssh = ssh
        self.is_connected = False
        self.last_checked = None

    @auto_renew_objects
    def disconnect_ssh(self, remove_from_used=False):
        if remove_from_used and self.ssh is not None:
            self.used_ssh_list.remove(self.ssh)
        self.assign_ssh(None)

    @auto_renew_objects
    def reset_status(self):
        super().reset_status()
        self.public_ip = ''
        self.ssh = None
        self.is_connected = False
        self.used_ssh_list.clear()
        self.is_working = False
