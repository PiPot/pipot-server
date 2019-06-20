#!/bin/bash

# Script expects 6 or more arguments:
# - log file
# - image name (deployment_{id}_{name}.img)
# - json config
# - hostname
# - root password
# - debug
# - wlan config (optional)
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
LOG="${DIR}/${1}_$(date +%d-%m-%Y-%H-%M-%S)_output.txt"
PROGRESS="${DIR}/${1}_$(date +%d-%m-%Y-%H-%M-%S)_progress.txt"
IMAGE_DIR="${DIR}/../honeypot_images"
echo "0" > "${PROGRESS}"
echo "" > "${LOG}"
echo "Starting create_image.sh" >> "${LOG}" 2>&1
if [ "$#" -lt 6 ]; then
	echo "Illegal number of arguments provided!" >> "${LOG}" 2>&1
	echo "Expected 6 or more arguments, got $#" >> "${LOG}" 2>&1
	echo "Given arguments: $@" >> "$"
    return -1
fi
if [ -a "${IMAGE_DIR}/${2}" ]; then
    echo "Deleting existing image: ${IMAGE_DIR}/${2}" >> "${LOG}" 2>&1
    rm "${IMAGE_DIR}/${2}" >> "${LOG}" 2>&1
fi
# Copy base to new name
echo "Creating 3GB image in ${IMAGE_DIR}/${2}" >> "${LOG}" 2>&1
dd bs=1M count=3072 if=/dev/zero of="${IMAGE_DIR}/${2}" >> "${LOG}" 2>&1
echo "5" > "${PROGRESS}"
echo "Finished creation, creating loop devices" >> "${LOG}" 2>&1
losetup -f "${IMAGE_DIR}/base.img" >> "${LOG}" 2>&1
ORIG_LD=$(losetup -a | grep "base.img" | sed 's/\(.*\): .*/\1/')
losetup -f "${IMAGE_DIR}/${2}" >> "${LOG}" 2>&1
NEW_LD=$(losetup -a | grep "${2}" | sed 's/\(.*\): .*/\1/')
echo "Copy data from base (${ORIG_LD}) to new image (${NEW_LD}) using dd" >> "${LOG}" 2>&1
dd if="${ORIG_LD}" of="${NEW_LD}" >> "${LOG}" 2>&1
echo "10" > "${PROGRESS}"
echo "Parted partition reorganisation" >> "${LOG}" 2>&1
startSector=$(fdisk -lu ${IMAGE_DIR}/${2} | grep Linux | sed -r 's/.*\.img2  *([0-9]+).*/\1/')
printf "d\n2\nn\np\n2\n${startSector}\n\nw\n" | fdisk ${IMAGE_DIR}/${2}
echo "20" > "${PROGRESS}"
echo "Get the image size" >> "${LOG}" 2>&1
rootOffset=$(expr ${startSector} \* 512)
echo "Creating loopback device for root partition with offset ${rootOffset}" >> "${LOG}" 2>&1
losetup -f -o ${rootOffset} "${IMAGE_DIR}/${2}" >> "${LOG}" 2>&1
ROOT_LD=$(losetup -a | grep "${2}" | grep "offset" | sed 's/\(.*\): .*/\1/')
echo "Checking partition ${ROOT_LD}" >> "${LOG}" 2>&1
e2fsck -f -y "${ROOT_LD}" >> "${LOG}" 2>&1
echo "Resizing partition ${ROOT_LD}" >> "${LOG}" 2>&1
resize2fs "${ROOT_LD}" >> "${LOG}" 2>&1
echo "30" > "${PROGRESS}"
echo "Removing loop devices" >> "${LOG}" 2>&1
losetup -d "${ORIG_LD}" "${NEW_LD}" "${ROOT_LD}"
# Create dir if it doesn't exist
if [ ! -d /mnt/tmp/ ]; then
    echo "Making temp folder /mnt/tmp/" >> "${LOG}" 2>&1
    mkdir /mnt/tmp/ >> "${LOG}" 2>&1
fi
echo "Mounting image" >> "${LOG}" 2>&1
# Mount image on temp folder
mount -o loop,offset=${rootOffset} "${IMAGE_DIR}/${2}" /mnt/tmp/ >> "${LOG}" 2>&1
echo "Mounting proc & sys" >> "${LOG}" 2>&1
# Assign proc & sysfs
mount proc /mnt/tmp/proc -t proc >> "${LOG}" 2>&1
mount sysfs /mnt/tmp/sys -t sysfs >> "${LOG}" 2>&1
echo "Copy necessary files" >> "${LOG}" 2>&1
cp -r "${DIR}/../../client" /mnt/tmp/usr/src/client >> "${LOG}" 2>&1
echo "${3}" > /tmp/profile.json
mv /tmp/profile.json /mnt/tmp/usr/src/client/honeypot_profile.json
cp -r "${DIR}/../pipot/services" /mnt/tmp/usr/src/client/pipot >> "${LOG}" 2>&1
cpuArch=$(lscpu | grep Architecture | sed 's/Architecture:  *\(.*\)/\1/')
if [ $(arch) != arm* ]; then
    echo "This is not arm machine, copy QemuUserEmulation binary to the chroot"  >> "${LOG}" 2>&1
    # Copy QemuUserEmulation binary to the chroot
    cp /usr/bin/qemu-arm-static /mnt/tmp/usr/bin >> "${LOG}" 2>&1
fi
# Chroot into it
echo "40" > "${PROGRESS}"
echo "Chrooting into image" >> "${LOG}" 2>&1
chroot /mnt/tmp /usr/src/client/bin/chroot.sh "/install-log.txt" "${4}" "${5}" "${6}" "${7}"  >> "${LOG}" 2>&1
cat /mnt/tmp/install-log.txt >> "${LOG}" 2>&1
echo "Exited chroot, unmounting proc & sys" >> "${LOG}" 2>&1
echo "90" > "${PROGRESS}"
if [ $(arch) != arm* ]; then
    # Remove QemuUserEmulation
    rm /mnt/tmp/usr/bin/qemu-arm-static >> "${LOG}" 2>&1
fi
# After exiting, unmount volumes
umount /mnt/tmp/proc && umount /mnt/tmp/sys >> "${LOG}" 2>&1
sleep 5
echo "Using fuser to kill any left processes" >> "${LOG}" 2>&1
fuser -k /mnt/tmp >> "${LOG}" 2>&1
echo "Unmount /mnt/tmp" >> "${LOG}" 2>&1
umount -l /mnt/tmp >> "${LOG}" 2>&1
echo "Unmounted, created image should be ready now" >> "${LOG}" 2>&1
echo "100" > "${PROGRESS}"
echo "Total runtime: ${SECONDS}" >> "${LOG}" 2>&1
