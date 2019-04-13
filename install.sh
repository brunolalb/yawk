#!/bin/sh

APP_FOLDER="/mnt/onboard/.apps/yawk/"

if [ ! -d $APP_FOLDER ]; then
    echo "Please move the application to the correct folder: $APP_FOLDER"
    exit -1
fi
if [ ! -e "$APP_FOLDER/yawk.py" ]; then
    echo "Please move the application to the correct folder: $APP_FOLDER"
    exit -1
fi
cd $APP_FOLDER

# first, check if the config.ini exists
if [ ! -e "config.ini" ]; then
    # let's create it
    correct = 'n'
    while [ correct != 'y' ]; do
        read -p "Enter your API key: " api
        read -p "Enter your city\'s ID" city
        echo
        echo "Your API key is \'$api\'"
        echo "Your city ID is \'$city\'"
        read -p "Correct? [yn] " correct
    done

    echo "[yawk]" > config.ini
    echo "key=$api" >> config.ini
    echo "city=$city" >> config.ini
fi

# create the automatic initializer
echo "#!/bin/sh" > /etc/init.d/yawk
echo "sleep 60" >> /etc/init.d/yawk
echo "cd $APP_FOLDER" >> /etc/init.d/yawk
echo "python yawk.py" >> /etc/init.d/yawk
chmod a+x /etc/init.d/yawk

# check if inittab already contains the yawk ocmmand
if grep -q "yawk" /etc/inittab; then
    # delete the line containing the yawk command
    sed -i '/yawk/d' /etc/inittab
fi
# add the command to start the yawk
echo "::sysinit:/etc/init.d/yawk" >> /etc/inittab

echo
echo "Yet Another Weather app for Kobo installed successfully!\n\n The eReader will restart now..."
sleep 5
reboot


