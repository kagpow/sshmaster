import asyncio
import logging
import time
from dataclasses import dataclass
from functools import cache
from typing import List

import asyncssh
import asyncssh.compression
import asyncssh.encryption
import asyncssh.kex
import asyncssh.mac

import utils
from utils import get_proxy_ip

logger = logging.getLogger('Ssh')


@cache
def get_algs_config():
    algs_config = dict(server_host_key_algs=[b'ssh-rsa'],  # Old dropbear servers compatibility
                       kex_algs=asyncssh.kex.get_kex_algs(),
                       encryption_algs=asyncssh.encryption.get_encryption_algs(),
                       mac_algs=asyncssh.mac.get_mac_algs(),
                       compression_algs=asyncssh.compression.get_compression_algs(),
                       signature_algs=(asyncssh.public_key.get_x509_certificate_algs() +
                                       asyncssh.public_key.get_public_key_algs()))

    # OpenSSH 7.2 compatibility
    if b'ecdh-sha2-nistp521' in algs_config['kex_algs']:
        algs_config['kex_algs'].remove(b'ecdh-sha2-nistp521')

    # Reverse order of kex_algs to prefer less secure algorithms
    algs_config['kex_algs'] = algs_config['kex_algs'][::-1]

    # Mimic JSCH config
    algs_config['kex_algs'] = (b'ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha1,'
                               b'diffie-hellman-group-exchange-sha256,diffie-hellman-group-exchange-sha1,'
                               b'diffie-hellman-group1-sha1'
                               .split(b','))
    algs_config['server_host_key_algs'] = (b'ssh-rsa,ssh-dss,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,'
                                           b'ecdsa-sha2-nistp521'
                                           .split(b','))
    algs_config['encryption_algs'] = (b'aes128-ctr,aes128-cbc,3des-ctr,3des-cbc,blowfish-cbc,aes192-ctr,'
                                      b'aes192-cbc,aes256-ctr,aes256-cbc'
                                      .replace(b'3des-ctr', b'')
                                      .split(b','))
    algs_config['mac_algs'] = b'hmac-md5,hmac-sha1,hmac-sha2-256,hmac-sha1-96,hmac-md5-96'.split(b',')
    algs_config['compression_algs'] = b'none'.split(b',')

    for key, algs in algs_config.items():
        algs_config[key] = [alg.decode() for alg in algs if alg]

    return algs_config


@dataclass
class ProxyInfo:
    port: int
    connection: asyncssh.SSHClientConnection
    host: str = 'localhost'
    proxy_type: str = 'socks5'

    @property
    def address(self):
        return f"{self.proxy_type}://{self.host}:{self.port}"


proxies: List[ProxyInfo] = []


class SSHError(Exception):
    """
    Exception for SSH-related issues.
    """


async def connect_ssh(host: str, username: str, password: str, port: int = None, ssh_port: int = 22,
                      retry: int = 3) -> ProxyInfo:
    """
    Connect to the SSH and returning the Socks5 proxy information.

    :param host: SSH host
    :param username: SSH username
    :param password: SSH password
    :param port: Local port to forward to
    :param ssh_port: SSH port (default: 22)
    :param retry: Number of retries (default: 3)
    :return: ProxyInfo object containing the forwarded Socks5 proxy
    """
    if not port:
        port = utils.get_free_port()

    try:
        await kill_proxy_on_port(port)
    except SSHError:
        pass

    start_time = time.time()
    ssh_info = f"{host:15} | {port:5}"

    def run_time():
        return '{:4.1f}'.format(time.time() - start_time)

    try:
        try:
            connection: asyncssh.SSHClientConnection = await asyncssh.connect(
                host, username=username, password=password, port=ssh_port,
                preferred_auth='password', known_hosts=None, **get_algs_config(),
                connect_timeout='30s', config=None
            )

            await connection.forward_socks('', port)
            proxy_info = ProxyInfo(port=port, connection=connection)

            if not await get_proxy_ip(proxy_info.address):
                await utils.kill_ssh_connection(connection)
                raise SSHError("Cannot connect to forwarded proxy.")
        except OSError as exc:
            if retry > 0:
                logger.info(f"{ssh_info} | Retrying... ({run_time()}s)")
                return await connect_ssh(host, username, password, port, ssh_port, retry - 1)
            else:
                raise SSHError(f"{type(exc).__name__}: {exc}.")
        except (asyncssh.Error, asyncio.TimeoutError) as exc:
            raise SSHError(f"{type(exc).__name__}: {exc}.")

    except SSHError as exc:
        logger.debug(f"{ssh_info} ({run_time()}s) - {exc}")
        raise

    else:
        logger.debug(f"{ssh_info} ({run_time()}s) - Connected successfully.")

    proxies.append(proxy_info)
    return proxy_info


async def verify_ssh(host: str, username: str, password: str, ssh_port: int = 22) -> bool:
    """
    Verify if SSH is usable.

    :param host: SSH host
    :param username: SSH username
    :param password: SSH password
    :param ssh_port: SSH port (default: 22)
    :return: True if SSH is connected successfully, returns False otherwise
    """
    try:
        proxy_info = await connect_ssh(host, username, password, ssh_port=ssh_port)
        await utils.kill_ssh_connection(proxy_info.connection)
        return True
    except SSHError:
        return False


async def kill_proxy_on_port(port: int):
    """
    Kill proxy on specified port number.

    :param port: Target port number
    """
    for proxy in proxies:
        if proxy.port == port:
            proxies.remove(proxy)
            await utils.kill_ssh_connection(proxy.connection)
            break
    else:
        raise SSHError(f"No proxy on port {port} found.")


if __name__ == '__main__':
    import logging

    logging.basicConfig(level=logging.DEBUG)


    async def main():
        ssh_str = '123.21.240.17|support|admin'
        print(await verify_ssh(*ssh_str.split('|')))


    asyncio.run(main())
