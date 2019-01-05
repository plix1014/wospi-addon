# plotstatistics

plot historical temperatur stats


### Prerequisites

* [Davis Vantage Pro2](https://www.davisinstruments.com/solution/vantage-pro2/) with solar radiation sensor
* [WOSPi](http://www.annoyingdesigns.com/wospi/) software
* python 'numpy' module
* python 'pandas' module


### Installing

copy files to your wospi installation.

e.g.: `/home/wospi/weather/`
```bash
cp plotStatistics.py /home/wospi/weather
cp plottemp_year.input/home/wospi/weather
```

### Python module installation

#### install numpy

```bash
sudo apt-get install python-numpy
```

#### install dev libs
```bash
sudo apt-get install python-dev
```

#### compile pandas
install pandas 0.14 ... there is no precomiled module available. You need to compile yourself
raspbian 7 (wheezy) only provides v. 0.8
takes quite a long time

If memory is < 1GB, temporarily increase temp mem with swap file
e.g.: Raspberry Model B Revision 2.0
```bash
$ sudo mkdir /home/swap
$ sudo dd if=/dev/zero of=/home/swap/swap0 bs=1M count=512
$ sudo chmod 0600 /home/swap/swap0 
$ sudo mkswap /home/swap/swap0 
$ sudo swapon /home/swap/swap0 
```

Download software
```bash
$ wget https://pypi.python.org/packages/source/p/pandas/pandas-0.14.1.tar.gz
```

no compile; takes quite a long time to compile(more than 2h)
```bash
$ tar xzf pandas-0.14.1.tar.gz
$ cd pandas-0.14.1
$ python setup.py build
#  => pandas-0.14.1-py2.7-linux-armv6l.egg
$ sudo python setup.py install
```

remove swap, if you needed it for compilation
```bash
$ sudo swapoff /home/swap/swap0 
$ rm -rf /home/swap

# Installation location/package
# /usr/local/lib/python2.7/dist-packages/
# pandas-0.14.1-py2.7-linux-armv6l.egg
```


### configure script
Set "DO_SCP=True", if png and image should be uploaded to your website.
temporary files and png are removed after the upload, if you don't want to delete, set 
```python
DO_SCP   = True
KEEP_PNG = False
KEEP_TMP = False
```

```python
# set LabelText to desired language.
#   LabelTextDE ... dictionary for german labels
#   LabelTextEN ... dictionary for english labels
#   set 'LabelText' to either dictionary
# 	 e.g. LabelText = LabelTextEN
LabelText = LabelTextEN

#   DEC_C    ... dictionary for the thresholds. Change only if you have different thresholds
DEG_C
```  

### set up cron jobs
to daily update the png, create following cron job:
daily: plotStatistics.py -c -f
one on January 1st.: plotStatistics.py -l 1

Before you add the cronjob, try to run the script manually
```
15 00   1 1 *   wospi  cd ~/wetter && python plotStatistics.py -l 1 -i y  >> /var/log/wospi/plotStatistics.log 2>&1
25 06   * * *   wospi  cd ~/wetter && python plotStatistics.py -c -f -i y >> /var/log/wospi/plotStatistics.log 2>&1
```

### configure Web layout

For HTML table formating, you can use `stats_addon.css` or you have your own style sheet. 
Only necessary, if you include `YYYY.statistics.inc` file into your web page.
		
		
## Example Charts

* [Weather Statistics](http://www.lidauer.net/wetter/wxstats.shtml)

## Author

* **plix1014** - [plix1014](https://github.com/plix1014)


## License

This project is licensed under the Attribution-NonCommercial-ShareAlike 4.0 International License - see the [LICENSE.md](LICENSE.md) file for details


## Acknowledgments

### Usage example

```bash
  usage: plotStatistics.py -c|-l n  -i y|m

		-c --current :	 current interval
		-l --last    :	 last interval, n ... number of years back
		-i --interval:	 y ... yearly, m ... monthly
                -f --fill    :   fill upcomming months of current year with empty data
		
	Result files:
		plottemp_YYYY.png	... gnuplot image
		YYYY.statistics.inc	... html table used as server side include
		

	to create statistics for previous years, run manually
	last year (2016):
		plotStatistics.py -l 1
		
	year bevor last year (2015):
		plotStatistics.py -l 2
```


### Notes:

 - script only uses celsius degrees. If you want the limits shown as fahrenheit
   you need to convert TICE,TFRE,TSUM,THEA,TDES,TTRO in the *.input file
 - definition of cold- ,hot-days, trop nights differ between countries
   current thresholds are valid for austria/germany/swiss as shown on
   https://de.wikipedia.org/wiki/Klimatologie or DWD (Deutscher Wetterdienst)
   if you need to change this limits(DEG_C), you need to convert your °F to °C
   e.g. Hot day:
           AT: Tmax >= 30°C
           US: Tmax >= 91°F = 32.8°C

 - set LabelText to desired language. This does not change the calculation


  
- short overview of the program logic
```
	 I. prepare pandas array
		1. merge csv' from requested year to on file
		2. load data into pandas array (all columns, although currently only outside temp is used)
		3. rename columns
		4. tell pandas, that first column is a datetime
		5. set first column as index

	 II. calc temperature statistics
		1. get outside_air_temp column
		2. get a 6h time shifted outside_air_temp column (for trop night calc.)
		3. resample by day
		4. get a min, max, mean and trop record
		5. rename columns
		6. build new dataframe
		7. calc the additional key figures
			- set flag if threshold reached
			- change boolean to numeric

		8. resample by month, sum up
		9. sort dataframe for a consistent output
		10. rename columns to a usable label

	 III. output dataframe
		1. save to csv for gnuplot
		2. build new dataframe for output
			- add sum row
			- create new header
			- rename timestamp column to monthname
		3. save monthy dataframe to html table
		4. run gnuplot
		5. transfer include and png files
```

