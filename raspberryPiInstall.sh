#! /bin/sh
sudo sed '/exit/ i sudo startx /usr/bin/python /home/pi/monkeyprint/monkeyprint.py --server' /etc/rc.local &
#sudo cp ./raspberryPiStartup.sh /etc/init.d/
#sudo chmod 755 /etc/init.d/raspberryPiStartup.sh
#sudo update-rc.d raspberryPiStartup.sh defaults
