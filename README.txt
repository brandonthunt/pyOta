=== Installing transmit/receive record scripts ===
		Author: Brandon Hunt
	   Date created: August 25th, 2022

============== Install instructions ==============
1) Open a terminal window and navigate to the directory containing the installation scripts. The 	directory should contain the files "installRemote.sh", "README.txt", and a folder named "sh".

2) Begin installing by running the command "./installRemote.sh"

3a) If there are no installation errors, two desktop icons corresponding to the Tx/Rx scripts should appear.
	- These may need additional permissions to let ubuntu run the .desktop as an executable; if 
	  so, right click on the icon, press "properties", click the center tab and toggle the 
	  checkbox that says "allow execution" (or similar). Apply the changes.
	- Right click on the desktop icon again and click "allow launching" if available. The script
	  should now launch when clicked. 

3b) If there are installation errors, contact me or attempt to debug following the error messages.
	- If the files were copied to $HOME/Software, then trying to run either "./launchRx.sh" or 
	  "./launchTx.sh". If these begin the scripts, then the problem is in the .desktop file. 
	  Otherwise, the problem may be with the path in the "launch(Tx/Rx).sh" scripts.
 
