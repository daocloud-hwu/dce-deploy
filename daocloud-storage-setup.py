#!/usr/bin/env python2
# encoding=utf-8

import json
import subprocess
import time

import os
import re

DEFAULT_VOLUME_GROUP = 'docker'


class UserError(Exception):
    pass


class SetupStorageFailed(Exception):
    pass


class DockerDaemonConfig(dict):
    __daemon_json_path__ = '/etc/docker/daemon.json'

    def __init__(self, *args, **kwargs):
        super(DockerDaemonConfig, self).__init__(*args, **kwargs)

    @classmethod
    def from_file(cls):
        origin_config = {}

        if os.path.exists(cls.__daemon_json_path__):
            with open(cls.__daemon_json_path__, 'r') as f:
                origin_config = json.loads(f.read())

        return cls(origin_config)

    def write_to_file(self):
        with open(self.__daemon_json_path__, 'w') as f:
            f.write(self.to_json())

    def merge_extra_config(self, extra_config):
        self.update(extra_config)

    def to_json(self):
        return json.dumps(self, indent=4)


class DockerStorageConfig(object):
    __support_fields__ = [
        'STORAGE_DRIVER',
        'DEVS',
        'VG',
        'ROOT_SIZE',
        'DATA_SIZE',
        'MIN_DATA_SIZE',
        'CHUNK_SIZE',
        'GROWPART',
        'AUTO_EXTEND_POOL',
        'POOL_AUTOEXTEND_THRESHOLD',
        'POOL_AUTOEXTEND_PERCENT',
        'DEVICE_WAIT_TIMEOUT',
        'WIPE_SIGNATURES'
    ]
    __default_path__ = '/etc/sysconfig/docker-storage-setup'

    def __init__(self, **kwargs):
        super(DockerStorageConfig, self).__init__()
        self.config_data = {f: kwargs[f]
                            for f in self.__support_fields__ if f in kwargs}

    def data(self):
        return '\n'.join(['{}={}'.format(k.upper(), v)
                          for k, v in self.config_data.iteritems()])

    def write_to_file(self):
        with open(self.__default_path__, 'w') as f:
            f.write(self.data())


def _backup(filename):
    if not os.path.exists(filename):
        raise IOError("File %s not exist." % filename)
    else:
        bk_fname = "%s.%d" % (filename, time.time())
        os.rename(filename, bk_fname)
        return bk_fname


def check_docker_config():
    daemon_configs = ['/etc/sysconfig/docker-storage', ]

    with open('/dev/null', 'wb') as fnull:
        p = subprocess.Popen(['docker', 'info'], stdout=fnull, stderr=fnull)
        exit_code = p.wait()

    if exit_code == 0:
        raise UserError(
            "Docker is running, please stop it and backup your graph data.")

    if os.path.exists('/var/lib/docker'):
        raise UserError("""Docker has been previously configured.
Please remove or rename /var/lib/docker directory first.""")

    exist_configs = [c for c in daemon_configs if os.path.exists(c)]
    for c in exist_configs:
        bk_fname = _backup(c)
        print "File %s has been rename to %s." % (c, bk_fname)


def force_input(prompt, default=None):
    while True:
        answer = raw_input(prompt).strip().lower()
        if answer:
            return answer


def yesno(prompt):
    while True:
        answer = force_input(prompt).strip().lower()

        if answer == "y" or answer == "yes":
            return True
        elif answer == "n" or answer == "no":
            return False
        else:
            continue


def _parse_docker_storage_daemon_params():
    if not os.path.exists('/etc/sysconfig/docker-storage'):
        raise IOError("File /etc/sysconfig/docker-storage not found.")

    with open('/etc/sysconfig/docker-storage', 'r') as f:
        data = f.read()

    config = {
        'storage-driver': None,
        'storage-opts': []
    }
    matched = re.search(r'--storage-driver (\S+)', data)
    if matched:
        config['storage-driver'], = matched.groups()

    config['storage-opts'] = re.findall(r'--storage-opt (\S+)', data)
    return {k: v for k, v in config.iteritems() if v}


def _parse_as_table(output):
    splited_data = [re.findall(r'(\S+)', line)
                    for line in output.splitlines() if 'WARNING' not in line]
    warnings = [line for line in output.splitlines() if 'WARNING' in line]
    if len(splited_data) < 2:
        return [], []

    fields = splited_data[0]
    return [dict(zip(fields, line)) for line in splited_data[1:]], warnings


def config_docker_daemon():
    origin_config = DockerDaemonConfig.from_file()
    origin_config.merge_extra_config(_parse_docker_storage_daemon_params())

    origin_config.write_to_file()


def list_block_devices():
    subprocess.call(['lsblk', '-a', '--output', 'NAME,SIZE,FSTYPE,MAJ:MIN,RM,RO,TYPE,MOUNTPOINT'])


def list_volume_groups():
    subprocess.call(['vgs', '-a'])


def get_volume_groups():
    p = subprocess.Popen(['vgs', '-a'], stdout=subprocess.PIPE)
    output, _ = p.communicate()

    lines, warnings = _parse_as_table(output)
    return {line['VG']: line for line in lines}, warnings


def get_logical_volumes():
    p = subprocess.Popen(['lvs', '-a'], stdout=subprocess.PIPE)
    output, _ = p.communicate()

    lines, warnings = _parse_as_table(output)
    return {line['LV']: line for line in lines}, warnings


def create_volume_group(vg_name, device):
    return subprocess.call(['vgcreate', vg_name, device])


def _remove_missing_volumes():
    vgs, _ = get_volume_groups()
    for vg in vgs:
        subprocess.call(['vgreduce', '--removemissing', '--force', vg])


def _do_setup(devices=None, vg=None, wipe_signature=False, ignore_missing=False):
    if devices is not None and vg is not None:
        raise UserError("Can't specify device and volume group in same time.")
    if devices is None and vg is None:
        raise UserError("You have to specify a device or a volume group.")

    storage_config_path = '/etc/sysconfig/docker-storage'
    if os.path.exists(storage_config_path):
        os.remove(storage_config_path)

    options = {
        'WIPE_SIGNATURES': 'true' if wipe_signature else 'false'
    }

    failed_target = 'device' if devices else 'volume group'
    if devices:
        options['DEVS'] = devices
    if vg:
        options['VG'] = vg

    DockerStorageConfig(**options).write_to_file()
    p = subprocess.Popen(['docker-storage-setup'],
                         stderr=subprocess.PIPE)

    while p.poll() is None:
        err_line = p.stderr.readline()
        if err_line != '':
            print err_line
        time.sleep(0.5)

    _, error = p.communicate()
    # print error
    if p.returncode != 0 and 'WIPE_SIGNATURES=true' in error:
        if yesno("Setup volume failed, try to wipe signature?(It maybe will lose your all data!)[Y/N]"):
            options['WIPE_SIGNATURES'] = True
            _do_setup(devices=devices, vg=vg, wipe_signature=True)
    elif not ignore_missing and ((p.returncode != 0) and
                                     ('vgreduce --removemissing' in error) or
                                     ('not found or rejected by a filter' in error)):
        if yesno("Missing volume found, this will cause unexpected problem, try to remove missing volumes?[Y/N]"):
            _remove_missing_volumes()
            _do_setup(devices=devices, vg=vg, wipe_signature=wipe_signature, ignore_missing=True)
    elif p.returncode != 0:
        raise SetupStorageFailed(
            "Setup storage pool %s %s failed." % (failed_target, failed_target))
    else:
        pass


def setup_with_device(device):
    if not device.startswith('/'):
        device = '/dev/' + device

    if not os.path.exists(device):
        raise IOError("Device %s not exist." % device)

    vgs, _ = get_volume_groups()
    if not vgs:
        print "No volume group found, will create a default volume group."
        exit_code = create_volume_group(DEFAULT_VOLUME_GROUP, device)
        if exit_code != 0:
            raise SetupStorageFailed("Create default volume group with name %s failed." % DEFAULT_VOLUME_GROUP)
        return _do_setup(vg=DEFAULT_VOLUME_GROUP, ignore_missing=True)

    return _do_setup(devices=device)


def setup_with_volume_group(vg):
    volume_groups, _ = get_volume_groups()
    if vg not in volume_groups:
        raise IOError("Volume group %s not exist." % vg)

    return _do_setup(vg=vg, ignore_missing=True)


def main():
    def main_func():
        check_docker_config()

        with_device, with_volume_group = False, False

        with_device = yesno(
            "Do you have special block storage device for Docker?[Y/N]")
        if with_device:
            list_block_devices()
            device = force_input(
                "Please specify a device to config storage pool: ")
            if device:
                setup_with_device(device)
            else:
                raise UserError("You have to specify a device.")
        else:
            with_volume_group = yesno(
                "Do you have special volume group for Docker?[Y/N]")
            if with_volume_group:
                list_volume_groups()
                vg = force_input(
                    "Please specify a volume group to config storage pool: ")
                if vg:
                    setup_with_volume_group(vg)
                else:
                    raise UserError("You have to specify a volume group.")

        if with_device or with_volume_group:
            config_docker_daemon()
            print "Config Docker daemon succeed."
        else:
            print "Exited."

    try:
        main_func()
    except SetupStorageFailed as e:
        print "FAILED: %s" % e.message
        exit(1)
    except KeyboardInterrupt:
        print ""
    except Exception as e:
        # import traceback
        # traceback.print_exc()
        print "ERROR: %s" % e.message
        exit(1)
    else:
        exit(0)


if __name__ == '__main__':
    main()
