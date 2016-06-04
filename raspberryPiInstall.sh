#! /bin/sh
sudo cp ./raspberryPiStartup.sh /etc/init.d/
sudo chmod 755 /etc/init.d/raspberryPiStartup.sh
sudo update-rc.d raspberryPiStartup.sh defaults
