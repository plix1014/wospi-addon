#!/bin/bash
#-------------------------------------------------------------------------------
# Name:        backup_wospi.sh
# Purpose:     sends additional backup of wospi data to FritzBox
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     09.04.2014
# Copyright:   (c) Peter Lidauer 2014
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changed:
#   PLI, 31.12.2015: add fritzbox backup
#-------------------------------------------------------------------------------

BK_DIR=/backup/tmp
BK_USER=wospi
BK_NAME=wospi_full_backup.tgz

DATE=$(date +'%Y%m%d_%H')

ALTERNATE_BK_SERVER=192.168.20.254

BACKUP2NAS=0

#-------------------------------------------------------------------------------

if [ ! -d "$BK_DIR" ]; then
    mkdir $BK_DIR
fi

if [ ! -d "$BK_DIR" ]; then
    echo "ERROR: backup directory '$BK_DIR' does not exist"
    exit 2
fi

echo "$(date +'%a %b %d %T %Y LT:') Backing up locally to $BK_DIR/$BK_NAME."
dpkg -l > /home/$BK_USER/backup/dpkg.list
sudo tar czf $BK_DIR/$BK_NAME /etc /root /home/wx /home/wospi /home/peter

if [ $BACKUP2NAS -eq 1 ]; then
    ping -c 2 $ALTERNATE_BK_SERVER >/dev/null 2>&1
    if [ $? -eq 0 ]; then
	echo "$(date +'%a %b %d %T %Y LT:') saving $BK_NAME at $ALTERNATE_BK_SERVER"
	cd ${BK_DIR}
        ftp $ALTERNATE_BK_SERVER <<-EOF
	put $BK_NAME
	bye
	quit
	EOF
    else
	echo "$(date +'%a %b %d %T %Y LT:') $ALTERNATE_BK_SERVER seems to be down."
    fi
else
    echo "$(date +'%a %b %d %T %Y LT:') Backup 2 $ALTERNATE_BK_SERVER is disabled"
fi

