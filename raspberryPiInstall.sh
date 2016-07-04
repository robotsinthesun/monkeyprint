#! /bin/sh
sudo sed -i '/^exit/ i sudo startx /usr/bin/python /home/pi/monkeyprint/monkeyprint.py --server' /etc/rc.local &
sudo sed -i "/enable_uart=0/c\enable_uart=1" /boot/config.txt &
