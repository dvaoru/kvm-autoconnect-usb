# kvm-autoconnect-usb
This is a Python script that automates the process of connecting a USB device to a KVM virtual machine. The USB device will be automatically attached to the guest when it is connected to the host and detached when it is disconnected.

## Deploy the script
Download:
```
wget https://github.com/dvaoru/kvm-autoconnect-usb/blob/main/kvm-autoconnect-usb.py
```
Make executable:
```
sudo chmod +x kvm-autoconnect-usb.py
```
## Usage
Run the script on the KVM host machine.

For starting monitoring a USB device and autoconnection to a virtual machine:
```
sudo python kvm-autoconnect-usb.py start <usb_vendor_id>:<usb_model_id> <vm_domain_name>
```
Example:
```
sudo python kvm-autoconnect-usb.py start 03f0:002a my_debian_vm
```


For stopping monitoring a USB device and autoconnection to a virtual machine:
```
sudo python kvm-autoconnect-usb.py stop <usb_vendor_id>:<usb_model_id> <vm_domain_name>
```
Example:
```
sudo python kvm-autoconnect-usb.py start 03f0:002a my_debian_vm
```


For getting a list of USB devices that are automatically connected to the guest:
```
sudo python kvm-autoconnect-usb.py list
```


For stopping autoconnecting all USB devices:
```
sudo python kvm-autoconnect-usb.py clear
```

## How it works under the hood

The script creates a udev rules file `/etc/udev/rules.d/80-kvm-autoconnect-usb.rules` for monitoring connecting and disconnecting USB devices, 
and creates a bash file `/usr/local/bin/kvm-autoconnect-script.sh` to attach and detach the devices to virtual machine by using `virsh`.

## Inspired by
+ [Nick Pegg](https://gist.github.com/nickpegg/417cf5024b765c3c92cbfbd725310091)
+ [usb-libvirt-hotplug](https://github.com/olavmrk/usb-libvirt-hotplug)


## Feedback
If you have any question, email me at [dvaoru@gmail.com](https://mail.google.com/mail/u/0/?view=cm&fs=1&tf=1&source=mailto&to=dvaoru@gmail.com)





