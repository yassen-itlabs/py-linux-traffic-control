"""
TODO: doc

"""
import os
from os.path import join as pjoin
from unittest.mock import MagicMock

from pyltc.util.cmdline import CommandLine
from pyltc.core import DIR_EGRESS, DIR_INGRESS
from pyltc.core.tfactory import default_target_factory


class DeviceManager(object):

    #: /sys/class/net/ path
    SYS_CLASS_NET = pjoin(os.sep, "sys", "class", "net")

    @classmethod
    def all_iface_names(cls, filter=None):
        result = []
        for filename in os.listdir(cls.SYS_CLASS_NET):
            if not filter or filter in filename:
                result.append(filename)
        return result

    @classmethod
    def load_module(cls, name, **kwargs):
        """Loads given module into kernel. Any kwargs are passed as key=value pairs."""
        kwargs_str = " ".join('{}={}'.format(k, v) for k, v in kwargs.items())
        CommandLine('modprobe {} {}'.format(name, kwargs_str), sudo=True).execute()

    @classmethod
    def remove_module(cls, name):
        """Removes given module from kernel."""
        CommandLine('modprobe --remove {}'.format(name), sudo=True).execute()

    @classmethod
    def shutdown_module(cls, name):
        """Sets down all module-related devices, then removes module from kernel."""
        for ifname in cls.all_iface_names(filter=name):
            cls.device_down(ifname)
            cls.remove_module(name)

    @classmethod
    def split_name(cls, name):
        module = name.rstrip("0123456789")
        num = name[len(module):]
        return module, int(num) if num else None

    @classmethod
    def device_exists(cls, name):
        return name in cls.all_iface_names()

    @classmethod
    def device_add(cls, name):
        assert not cls.device_exists(name), 'Device already exists: {!r}'.format(name)
        module, _ = cls.split_name(name)
        CommandLine("ip link add {} type {}".format(name, module), sudo=True).execute()

    @classmethod
    def device_is_down(cls, name):
        """Returns True if given network device down, otherwise returns False.
        Consults /sys/class/net/{device-name}/operstate.

        :return: bool
        """
        assert cls.device_exists(name), "Device does not exist: {!r}".format(name)
        with open(pjoin(cls.SYS_CLASS_NET, name, 'operstate')) as fhl:
            return 'down' == fhl.read().strip().lower()

    @classmethod
    def device_up(cls, name):
        assert cls.device_exists(name), 'Device does NOT exist: {!r}'.format(name)
        CommandLine("ip link set dev {} up".format(name), sudo=True).execute()

    @classmethod
    def device_down(cls, name):
        assert cls.device_exists(name), 'Device does NOT exist: {!r}'.format(name)
        CommandLine("ip link set dev {} down".format(name), sudo=True).execute()


class NetDevice(object):

    @classmethod
    def minimal_nonexisting_name(cls, module):
        """TODO: doc
        :param module:
        :return:
        """
        existing_names = DeviceManager.all_iface_names(module)
        if not existing_names:
            return "{}0".format(module)
        lst = sorted([DeviceManager.split_name(name) for name in existing_names], key=lambda tpl: tpl[1])
        num = lst[-1][1] + 1
        return "{}{}".format(module, num)

    @classmethod
    def get_device(cls, name_or_module):
        """Returns a NetDevice instance that either wraps an existing device
        with given name. The device is added first if it does not yet exist.
        If only the module name is given (e.g. 'ifb') then the first available
        device name is picked.

        :param name_or_module: string - device name or module name
        :return: NetDevice
        """
        if name_or_module in DeviceManager.all_iface_names():
            return cls(name_or_module)
        module, num = DeviceManager.split_name(name_or_module)
        if num is None:
            new_name = cls.minimal_nonexisting_name(module)
        else:
            new_name = "{}{}".format(module, num)
        DeviceManager.load_module(module)
        DeviceManager.device_add(new_name)
        return cls(new_name)

    def __init__(self, name, target_factory=None):
        assert isinstance(name, str)
        self._name = name
        if not target_factory:
            target_factory = default_target_factory
        self._egress_chain = target_factory(self, DIR_EGRESS)
        self._ingress_chain = target_factory(self, DIR_INGRESS)
        self._ifbdev = None

    @classmethod
    def new_instance(cls, name, target_factory=None):
        """
        TODO: document
        """
        if name is None:
            return MagicMock()
        if target_factory is None:
            target_factory = default_target_factory
        return cls(name, target_factory)

    @property
    def name(self):
        return self._name

    @property
    def egress(self):
        return self._egress_chain

    @property
    def ingress(self):
        """Returns the ingress chain builder for this interface.
        :return: ITarget - the ingress chain target builder
        """
        return self._ingress_chain

    def exists(self):
        return DeviceManager.device_exists(self._name)

    def is_up(self):
        return not DeviceManager.device_is_down(self._name)

    def is_down(self):
        return DeviceManager.device_is_down(self._name)

    def add(self):
        DeviceManager.device_add(self._name)

    def up(self):
        DeviceManager.device_up(self._name)

    def down(self):
        DeviceManager.device_down(self._name)


class IfbDevice(NetDevice):

    @classmethod
    def load_module(cls):
        DeviceManager.load_module('ifb')

    @classmethod
    def remove_module(cls):
        DeviceManager.remove_module('ifb')

    @classmethod
    def shutdown_module(cls):
        DeviceManager.shutdown_module('ifb')

    @classmethod
    def get_device(cls, name_or_module=None):
        return NetDevice.get_device(name_or_module or 'ifb')