# satimage

download images from NASA Worldview and combines it to an animated gif

Download code by Brian Blaylock University of Utah
* [kbkb-wx-python.blogspot.co.at](http://kbkb-wx-python.blogspot.co.at/2015/08/download-satellite-images-from-nasa.html)

Added code to combine ten(back five days, two images per day) jpeg images into one animated gif.


### Prerequisites

* [WOSPi](http://www.annoyingdesigns.com/wospi/) software
* python 'numpy' module
* python 'pillow' module
* python 'images2gif' module


### Installing

copy files to your wospi installation.

e.g.: /home/wospi/weather/
```
cp satimage.py /home/wospi/weather
```

install python module ephem
```
$ sudo apt-get install python-numpy
$ sudo pip2 install pillow
$ sudo pip2 install images2gif
```


### Configuration

Goto NASA's Worldview https://earthdata.nasa.gov/labs/worldview/
* 1) select 'Introduction to Worldview' icon
* 2) zoom in to desired location
* 3) click "take a snapshot" icon
* 4) Draw the region you wish to take a photo
* 5) Modify the URL below, particularly the lat and lon
* 6) copy the URL and paste it to an editor or note the boxsize and the coordinates
* 7) use values from URL and configure the variabels EXTENT, WIDTH and HEIGHT in main()


check the gif file. If everything is fine, activate SCP transfer (DO_SCP=True) and add it to your HP.

setup the cronjobs to run the script once a day
```
# upload satellite image
06 05   * * *   wospi  cd ~/tools   && python satimage.py      > /var/log/wospi/satimage.log 2>&1
```


## Example Charts

* [Satellite Image](http://www.lidauer.net/wetter/24h_plots.html)


## Author

* Brian Blaylock [kbkb-wx-python.blogspot.co.at](http://kbkb-wx-python.blogspot.co.at/2015/08/download-satellite-images-from-nasa.html)
* **plix1014** - [plix1014](https://github.com/plix1014)


## License

This project is licensed under the Attribution-NonCommercial-ShareAlike 4.0 International License - see the [LICENSE.md](LICENSE.md) file for details


## Acknowledgments


