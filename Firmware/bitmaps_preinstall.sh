#!/bin/sh
# =================================================================================
# Name:			bitmaps_preinstall.sh
#
# Description:	Pre-installation script for Jade SWDL of bitmap images file via CAN
#
# This script is downloaded and executed before any application files.
# It can be used to check flash drive integrity, predelete old files etc
#
# Also, the execution time of all commands in this script must not excede 5 min
# (VBF generator appends a minimum of 6 EOF blocks allowing @55s each block) 
# =================================================================================
echo "** BITMAPS PRE_INSTALL ACTIONS**"


# =================================================================================
# start the FLASH driver if not running
# =================================================================================
if [ "$(pidin | grep devf-visteon-u554)" != "" ]
then
	echo "FLASH driver is running"
else
	#echo "sending SIGKILL to devf-visteon-u554"
	#killbyname devf-visteon-u554
	#sleep 20
	echo "starting the FLASH driver with automount disabled, no reclaim, and full verify"
	devf-visteon-u554  -s 0x08000000,256M -a -f3 &
echo "waitfor flash driver to start"
fi
waitfor /dev/fs0 30

#waitfor will exit with 0 if successful.
if [ $? -ne 0 ] 
then
	echo "ERROR! flash driver did NOT start properly!"
	exit 1
fi



# =================================================================================
# Can normally safely erase flash partition while a CAN download is ongoing, since 
# the erase takes 5s/MByte whereas CAN download takes 60s/Mbyte (or 24s/Mbyte 
# when compression is used). However, the raw bitmaps partition is a special case,  
# since compression ratios of up to 95% are common for images. That means the  
# download rate is effectively 3s/Mbyte i.e. FASTER THAN THE ERASE !
#
# FORTUNATELY, for downloads on top of X351/L322 releases after 21st August 09, the  
# post-download scripts use pidin and grep to checks for completion of the flashctl
# erase process.
# 
# HOWEVER.. earlier versions did not have grep installed - in that case, the 
# postinstall script cannot determine the status of the erase process, so we must
# fully erase the partition before allowing the CAN download to start.
# =================================================================================
echo "Starting background erase"
flashctl -p /dev/fs0 -o 112m -l 144m -e -vvv &
exit 0
