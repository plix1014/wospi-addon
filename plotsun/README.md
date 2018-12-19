
INSTALL sun plot script
--------------------------------------------------

1. copy files to your wospi installation.

   e.g.: /home/wospi/weather/

   cp plotSun.py /home/wospi/weather
   cp plotsun_full.input /home/wospi/weather
   cp plotsun_shine.input /home/wospi/weather
   cp store_sunrise_set_times.sh /home/wospi/weather


2. add additional parameters to config.py
   a)   
     cat config.addon >> /home/wospi/weather/config.py

   or 
   b)
     use vim to copy parameters to config.py

     vim -p config.py config.addon

   edit TOWN. 


3. install python module ephem

  $ sudo pip install ephem


4. store sun data

  check and edit WOSPI_HOME in script

  $ store_sunrise_set_times.sh

  This script stores the times from
      /var/tmp/sunrise.tmp  
      /var/tmp/sunset.tmp
  in CSVPATH/suntimes.csv 

  you probably need to run this script several days, bevor you can plot the first chart
  If you don't want to wait, you can download weather data. See below


5. run plot script

  python plotSun.py

  check the png. If everything is fine, activate SCP transfer (DO_SCP=True) and add it to your HP.


6. setup the cronjobs
  run the script once a day

    05 06   * * *   wospi  cd ~/weather && ./store_sunrise_set_times.sh > /var/log/store_suntimes.log 2>&1
    08 06   * * *   wospi  cd ~/weather && python plotSun.py            > /var/log/plotSun.log 2>&1


#################################################################################

7. download initial suntimes data and convert file to required format
   you can either (a) download and convert the file with the convertsolardata.py script
   or download the file yourself, copy it the the CSVPATH, run the script, and rename the result (b)

  a) Edit convertsolardata.py
      set GPS position, timezone, elevation, ...
	latitude
	longitude
	timezone
	elev
	press
	temp

    run convertsolardata.py
  	You should now have a 'suntimes_conv.csv' in your CSVPATH
	
    cd CSVPATH
    cp suntimes_conv.csv suntimes.csv

  
  b) go to https://www.nrel.gov/midc/solpos/spa.html
     and fill in your values and download the file

      copy it to CSVPATH/suntimes_url.csv

    now run convertsolardata.py
  	You should find a 'suntimes_conv.csv' in your CSVPATH
	
    cd CSVPATH
    cp suntimes_conv.csv suntimes.csv


