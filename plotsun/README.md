# plotsun

plot sunrise, sunset and sunshine charts based on sensor data


### Prerequisites

* [Davis Vantage Pro2](https://www.davisinstruments.com/solution/vantage-pro2/) with solar radiation sensor
* [WOSPi](http://www.annoyingdesigns.com/wospi/) software
* python 'ephem' module


### Installing

copy files to your wospi installation.

e.g.: /home/wospi/weather/
```
cp plotSun.py /home/wospi/weather
cp plotsun_full.input /home/wospi/weather
cp plotsun_shine.input /home/wospi/weather
cp store_sunrise_set_times.sh /home/wospi/weather
```


add additional parameters to config.py
either:   
```
cat config.addon >> /home/wospi/weather/config.py
```

or: use vim to copy parameters to config.py
```
vim -p config.py config.addon
```

edit TOWN variable. 


install python module ephem
```
$ sudo pip install ephem
```

To store sun data check and edit WOSPI_HOME variable in script. 
Then run it:
```
$ store_sunrise_set_times.sh
```

This script gets the times from
```
/var/tmp/sunrise.tmp  
/var/tmp/sunset.tmp

and saves them to
```
CSVPATH/suntimes.csv 
```

you probably need to run this script several days, bevor you can plot the first chart
If you don't want to wait, you can download weather data. See below


Now manually run the plot script
```
python plotSun.py
```

check the png file. If everything is fine, activate SCP transfer (DO_SCP=True) and add it to your HP.

setup the cronjobs to run the script once a day
```
05 06   * * *   wospi  cd ~/weather && ./store_sunrise_set_times.sh > /var/log/store_suntimes.log 2>&1
08 06   * * *   wospi  cd ~/weather && python plotSun.py            > /var/log/plotSun.log 2>&1
```


### Optional step 
Optional, if you want to start with a pre calculated chart

You can either download initial suntimes data and convert file to required format
you can either (a) or download and convert the file with the convertsolardata.py script
or download the file yourself, copy it the the CSVPATH, run the script, and rename the result (b)

a) Edit convertsolardata.py
set GPS position, timezone, elevation, ...
latitude
longitude
timezone
elev
press
temp

run:
```
convertsolardata.py
```

You should now have a 'suntimes_conv.csv' in your CSVPATH

```
cd CSVPATH
cp suntimes_conv.csv suntimes.csv
```


b) go to https://www.nrel.gov/midc/solpos/spa.html
and fill in your values and download the file

```
copy it to CSVPATH/suntimes_url.csv
```

now run:
```
convertsolardata.py
```
You should find a 'suntimes_conv.csv' in your CSVPATH

```
cd CSVPATH
cp suntimes_conv.csv suntimes.csv
```


## Example Charts

* [Sunplot](http://www.lidauer.net/wetter/sunplots.html)

## Author

* **plix1014** - [plix1014](https://github.com/plix1014)


## License

This project is licensed under the Attribution-NonCommercial-ShareAlike 4.0 International License - see the [LICENSE.md](LICENSE.md) file for details


## Acknowledgments


