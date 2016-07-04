#! /bin/sh
sudo sed -i '/^exit/ i sudo startx /usr/bin/python /home/pi/monkeyprint/monkeyprint.py --server' /etc/rc.local &
