
This script creates some statistics about your temperature.
A bar graph image and a table representation of the various thresholds


1. Install Script and addons

a) Script 
	copy plotStatistics.py plottemp_chart.input and plottemp_year.input to your wospi installation 


b) addon modules

	# install numpy

	sudo apt-get install python-numpy

	
	# install pandas 0.14 ... there is no precomiled module available. You need to compile yourself
	# raspbian 7 (wheezy) only provides v. 0.8
	takes quite a long time

	# install dev libs
	sudo apt-get install python-dev

	# if memory is < 1GB, temporarily increase temp mem with swap file
	# e.g.: Raspberry Model B Revision 2.0
	sudo mkdir /home/swap
	sudo dd if=/dev/zero of=/home/swap/swap0 bs=1M count=512
	sudo chmod 0600 /home/swap/swap0 
	sudo mkswap /home/swap/swap0 
	sudo swapon /home/swap/swap0 

	# download software
	wget https://pypi.python.org/packages/source/p/pandas/pandas-0.14.1.tar.gz

	# compile; takes quite a long time to compile(more than 2h)
	tar xzf pandas-0.14.1.tar.gz
	cd pandas-0.14.1
	python setup.py build
	  => pandas-0.14.1-py2.7-linux-armv6l.egg
	sudo python setup.py install

	sudo swapoff /home/swap/swap0 
	rm -rf /home/swap

	# /usr/local/lib/python2.7/dist-packages/
	# pandas-0.14.1-py2.7-linux-armv6l.egg
	#

c) configure script
	Set "DO_SCP=True", if png and image should be uploaded to your website.
	temporary files and png are removed after the upload, if you don't want to delete, set 
	KEEP_PNG and KEEP_TMP to False

	set LabelText to desired language.
	  LabelTextDE ... dictionary for german labels
	  LabelTextEN ... dictionary for english labels
	  set 'LabelText' to either dictionary
		 e.g. LabelText = LabelTextEN

	DEG_C       ... dictionary for the thresholds. Change only if you have different thresholds
  
  
d) cron jobs
	to daily update the png, create following cron job:
	daily: plotStatistics.py -c -f
	one on January 1st.: plotStatistics.py -l 1

	
e) manual jobs	

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

	actually, the 'm' for monthly is not really usefull now. You can ignore it

f) Web 
	For HTML table formating, you can use stats_addon.css or you have your own style sheet. Only necessary, if you include YYYY.statistics.inc
	
	e.g.: http://www.lidauer.net/wetter/wxstats.shtml
		
		
g) Cron jobs
	you can setup the jobs as you like it, but this are the jobs I suggest
	# yearly job to finalize statistics of previous year
	15 00   1 1 *   wospi  cd ~/wetter && python plotStatistics.py -l 1  > /var/log/plotStatistics.log 2>&1
	# daily job. Best to run after 06:00 am
	25 06   * * *   wospi  cd ~/wetter && python plotStatistics.py -c -f >> /var/log/plotStatistics.log 2>&1


# Notes:
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


  
 short overview of the program logic
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


 Configuration options in config.py

 depends on:  WOSPi, numpy, pandas
