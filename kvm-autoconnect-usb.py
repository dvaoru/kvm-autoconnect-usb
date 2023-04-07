# coding=utf-8
import os
import subprocess
from collections import namedtuple
import argparse


class FileUtils:

    def __init__(self):
        pass

    # Get list of files in the path
    @staticmethod
    def get_files(path):
        for file in os.listdir(path):
            if os.path.isfile(os.path.join(path, file)):
                yield file

    # Write a text to file
    @staticmethod
    def write_file(path, text):
        with open(path, 'w') as f:
            f.write(text)

    # Runs the given function with elevated privileges using sudo.
    @staticmethod
    def do_with_ask_sudo(foo):
        command = "sudo -v && sudo python -c 'import sys; sys.path.append(\".\"); import {0}; {1}()'" \
            .format(foo.__module__, foo.__name__)
        subprocess.run(command, shell=True)

    # Copy file with sudo access
    @staticmethod
    def sudo_move_file_with_rewrite(source_file, target_folder_or_file):
        subprocess.call(['sudo', 'mv', '-f', source_file, target_folder_or_file])

    # Make a file executable
    @staticmethod
    def sudo_make_executable(file):
        subprocess.call(['sudo', 'chmod', 'ugo+x', file])

    # Create a file with sudo
    @staticmethod
    def sudo_create_file(file, text):
        temp = subprocess.check_output('mktemp')
        FileUtils.write_file(temp, text)
        FileUtils.sudo_move_file_with_rewrite(temp, file)

    # Remove a file
    @staticmethod
    def sudo_remove_file(file_name):
        subprocess.call(['sudo', 'rm', file_name])

    @staticmethod
    def find_files_with_string(folder_path, search_string):
        matching_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and search_string in open(file_path).read():
                    matching_files.append(file_path)
        return matching_files


# Class for usb info
UsbDevice = namedtuple('UsbDevice', ['name', 'vendor_id', 'model_id'])


def parce_usb_device(usb_id):
    vendor_id, model_id = usb_id.split(":")
    return UsbDevice('', vendor_id, model_id)


# Class for udev rule
UdevRule = namedtuple('UdevRule', ['domain', 'usb_device'])


class BashHelper:
    def __init__(self):
        self.create_bash_script()

    BASH_FILE = '/usr/local/bin/kvm-autoconnect-script.sh'

    def create_bash_script(self):
        FileUtils.sudo_create_file(self.BASH_FILE, self.get_bash_script_text())
        FileUtils.sudo_make_executable(self.BASH_FILE)

    def attach(self, usb, domain):
        subprocess.call(['sudo', self.BASH_FILE, 'attach', domain, usb.vendor_id, usb.model_id])

    def detach(self, usb, domain):
        subprocess.call(['sudo', self.BASH_FILE, domain, usb.vendor_id, usb.model_id])

    def detach_force(self, usb, domain):
        subprocess.call(['sudo', self.BASH_FILE, 'detach_force', domain, usb.vendor_id, usb.model_id])

    def get_bash_script_text(self):
        return '''#!/bin/bash
set -e

ACTION=$1
DOMAIN=$2
VENDOR=$3
MODEL=$4
        
CONF_FILE=$(mktemp --suffix=.kvm-udev)
cat << EOF >$CONF_FILE
<hostdev mode='subsystem' type='usb'>
  <source startupPolicy='optional'>
    <vendor id='0x$VENDOR'/>
    <product id='0x$MODEL'/>
  </source>
</hostdev>
EOF
if [ $ACTION == "attach" ]; then
    if virsh "detach-device" "$DOMAIN" "$CONF_FILE" --persistent; then
        echo "Detach successful"
    else
        echo "Detach unsuccessful"
    fi    
    if virsh "attach-device" "$DOMAIN" "$CONF_FILE" --persistent; then
        echo "Attach persistent" 
    else
        echo "Attach persistent fail"
        if virsh "attach-device" "$DOMAIN" "$CONF_FILE"; then
            echo "Attach"
        fi
    fi
elif [ "$ACTION" = "detach" ]; then
    if lsusb | grep -q "${VENDOR}:${MODEL}"; then
        echo "USB device ${VENDOR}:${MODEL} is connected."
    else
        echo "USB device ${VENDOR}:${MODEL} is not connected."  
        virsh "detach-device" "$DOMAIN" "$CONF_FILE"     
    fi
elif [ "$ACTION" = "detach_force" ]; then
    virsh "detach-device" "$DOMAIN" "$CONF_FILE" --persistent||
    echo "Detach force fail" 
else
    echo "Invalid argument"
fi

rm "$CONF_FILE"
'''


class UdevHelper:
    UDEV_FILE = '/etc/udev/rules.d/80-kvm-autoconnect-usb.rules'
    BASH_FILE = '/home/sasha/Python/KvmAutoconnectUsb/script.sh'
    INDICATOR_LABEL = '#Created automatically by kvm-autoconnect-usb.py'

    def __init__(self):
        pass

    def add_udev_rule(self, usb, domain, bash_file):
        rules_list = self.get_existing_rules()
        for item in rules_list:
            if item.usb_device.vendor_id == usb.vendor_id and item.usb_device.model_id == usb.model_id:
                rules_list.remove(item)
        rules_list.append(UdevRule(domain, usb))
        self.save_udev_file(rules_list, bash_file)
        self.sudo_reload_udev_rules()

    def remove_udev_rule(self, usb, domain, bash_file):
        rules_list = self.get_existing_rules()
        for item in rules_list:
            if item.usb_device.vendor_id == usb.vendor_id and item.usb_device.model_id == usb.model_id:
                rules_list.remove(item)
        if len(rules_list) == 0:
            self.delete_udev_file()
        else:
            self.save_udev_file(rules_list, bash_file)
        self.sudo_reload_udev_rules()

    def remove_all_udev_rules(self):
        self.delete_udev_file()
        self.sudo_reload_udev_rules()

    # Reload udev rules
    def sudo_reload_udev_rules(self):
        subprocess.call(['sudo', 'udevadm', 'control', '--reload-rules'])
        subprocess.call(['sudo', 'udevadm', 'trigger'])

    def create_udev_rule(self, script_path, usb_device, vm_name):
        text = 'ACTION=="bind", SUBSYSTEM=="usb", ENV{ID_VENDOR_ID}=="' + usb_device.vendor_id + '", ENV{ID_MODEL_ID}=="' + usb_device.model_id + '", RUN+="' + script_path + ' attach ' + vm_name + ' $env{ID_VENDOR_ID} $env{ID_MODEL_ID}"'
        text += "\n"
        text += 'ACTION=="remove", SUBSYSTEM=="usb", RUN+="' + script_path + ' detach ' + vm_name + ' ' + usb_device.vendor_id + ' ' + usb_device.model_id + '"'
        return text

    def save_udev_file(self, udev_rules_list, bash_file):
        text = self.INDICATOR_LABEL
        text += '\n'
        for rule in udev_rules_list:
            text += self.create_udev_rule(bash_file, rule.usb_device, rule.domain)
            text += '\n'
        FileUtils.sudo_create_file(self.UDEV_FILE, text)

    def delete_udev_file(self):
        FileUtils.sudo_remove_file(self.UDEV_FILE)

    @staticmethod
    def parse_udev_file(file_path):
        if not os.path.exists(file_path):
            return []
        with open(file_path) as f:
            content = f.readlines()
        ids = []
        for line in content:
            if 'ACTION=="bind"' in line:
                vendor_id = line.split("ENV{ID_VENDOR_ID}==\"")[1].split("\"")[0]
                model_id = line.split("ENV{ID_MODEL_ID}==\"")[1].split("\"")[0]
                domain = line.split(" attach ")[1].split(" ")[0]
                ids.append(UdevRule(domain, UsbDevice("", vendor_id, model_id)))
        return ids

    def get_existing_rules(self):
        list_rules = self.parse_udev_file(self.UDEV_FILE)
        return list_rules


class Manager:
    def __init__(self):
        self.bash_helper = BashHelper()
        self.udev_helper = UdevHelper()

    def start_auto_connect(self, usb, domain):
        self.bash_helper.attach(usb, domain)
        self.udev_helper.add_udev_rule(usb, domain, self.bash_helper.BASH_FILE)

    def stop_auto_connect(self, usb, domain):
        self.bash_helper.detach_force(usb, domain)
        self.udev_helper.remove_udev_rule(usb, domain, self.bash_helper.BASH_FILE)

    def print_connected_usb_list(self):
        rules_list = self.udev_helper.get_existing_rules()
        for l in rules_list:
            print (l.usb_device.vendor_id + ':' + l.usb_device.model_id + ' -> ' + l.domain)

    def clear_all_auto_connections(self):
        rules_list = self.udev_helper.get_existing_rules()
        for rule in rules_list:
            self.bash_helper.detach_force(rule.usb_device, rule.domain)
        self.udev_helper.remove_all_udev_rules()


def main():
    manager = Manager()
    # Create an ArgumentParser object and define the arguments
    parser = argparse.ArgumentParser(
        description='Automatically connect or disconnect a USB device to a KVM virtual machine.')

    parser.set_defaults(action='default_action')

    subparsers = parser.add_subparsers(help='usage: kvm-autoconnect-usb.py [-h] {start,stop} vendor_id:model_id domain')

    start_parser = subparsers.add_parser('start',
                                         help='Start monitoring the USB device and connect it to the KVM domain if it is plugged in. Requires the USB device and domain as arguments.')
    start_parser.set_defaults(action='start')

    start_parser.add_argument('usb', type=str,
                              help='The USB device in the format "vendor_id:product_id". For example, "046d:c018".')
    start_parser.add_argument('vm_name', type=str, help='The name of the KVM domain to connect the USB device to.')

    stop_parser = subparsers.add_parser('stop',
                                        help='Stop monitoring the USB device and connect it to the KVM domain if it is plugged in. Requires the USB device and domain as arguments.')
    stop_parser.set_defaults(action='stop')

    stop_parser.add_argument('usb', type=str,
                             help='The USB device in the format "vendor_id:product_id". For example, "046d:c018".')
    stop_parser.add_argument('vm_name', type=str, help='The name of the KVM domain to connect the USB device to.')

    list_parser = subparsers.add_parser('list', help='List of connected USB')
    list_parser.set_defaults(action='list')

    clear_parser = subparsers.add_parser('clear', help='Stop monitoring and remove all USB from all domains.')
    clear_parser.set_defaults(action='clear')

    # Parse the arguments
    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        return

    action = args.action

    if args.action == 'default_action':
        parser.print_help()

    elif action == 'start':
        usb_device = parce_usb_device(args.usb)
        manager.start_auto_connect(usb_device, args.vm_name)

    elif action == 'stop':
        usb_device = parce_usb_device(args.usb)
        manager.stop_auto_connect(usb_device, args.vm_name)

    elif action == 'list':
        manager.print_connected_usb_list()

    elif action == 'clear':
        manager.clear_all_auto_connections()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()

