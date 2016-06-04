#! /bin/sh
### BEGIN INIT INFO
# Provides:          monkeyprint in server mode
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Simple script to start a program at boot
# Description:       A simple script from www.stuffaboutcode.com which will start / stop a program a boot / shutdown.
### END INIT INFO

# If you want a command to always run, put it here

# Carry out specific functions when asked to by the system
case "$1" in
  start)
    echo "Starting Monkeyprint in server mode."
    # run application you want to start
    sudo startx /usr/bin/python $HOME/monkeyprint/monkeyprint.py --server
    ;;
  stop)
    echo "Stopping Monkeyprint."
    # kill application you want to stop
    killall monkeyprint.py
    ;;
  *)
    echo "Usage: /etc/init.d/raspberryPiStartup {start|stop}"
    exit 1
    ;;
esac

exit 0


