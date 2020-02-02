#!/bin/sh

APP_FOLDER="/mnt/onboard/.apps/yawk/"

if [ ! -d $APP_FOLDER ]; then
    echo "Application is not present or not in the correct folder: $APP_FOLDER"
    exit -1
fi

# check if inittab already contains the yawk command
if grep -q "yawk" /etc/inittab; then
    # delete the line containing the yawk command
    sed -i '/yawk/d' /etc/inittab
fi

echo "Remove the $APP_FOLDER, if desired"

echo
echo "All Good! The eReader will restart now..."
sleep 10
reboot