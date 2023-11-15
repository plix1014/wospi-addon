#!/usr/bin/env python
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Brian Blaylock
# University of Utah
# http://kbkb-wx-python.blogspot.co.at/2015/08/download-satellite-images-from-nasa.html

# Download True Color Images from NASA WorldView
# and add the time stamp to the image

## Images downloaded from NASA's Worldview
## https://earthdata.nasa.gov/labs/worldview/
# 1) select 'Introduction to Worldview' icon
# 2) zoom in to desired location
# 3) click "take a snapshot" icon
# 4) Draw the region you wish to take a photo
# 5) Modify the URL below, particularly the lat and lon
# 6) copy the URL and paste it to an editor or note the boxsize and the coordinates
# 7) use values from URL and configure the variabels EXTENT, WIDTH and HEIGHT in main()

# added code to generate gif

# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no

# Author:      Peter Lidauer <plix1014@gmail.com>
#
# Created:     17.12.2015
# Copyright:   (c) Brian Blaylock, Peter Lidauer 2015
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
#-------------------------------------------------------------------------------
# Changes:
#  PLI, 30.10.2023: adjustments for container image
#  PLI, 02.11.2023: add watermark color
#  PLI, 15.11.2023: read HOMEPATH from environment
#

import sys, os

CONFIG_HOME = os.environ.get('HOMEPATH')
sys.path.append(CONFIG_HOME + '/')

import urllib
import time
from datetime import datetime, timedelta, date
import numpy as np

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageSequence
from images2gif import writeGif
from fnmatch import fnmatch
import imghdr

from config import SCPTARGET, SCP

# font for watermark text
#FONT = 'DejaVuSans.ttf'
FONT = 'DejaVuSansMono.ttf'

# save dir for jpeg images
outdir = '/var/tmp/'

# gif file name
outgif = outdir + 'radar.gif'

# number of days bevor today to start
NUMDAYS=-5

# print debug info
DEBUG=False

KEEP_GIF=False
KEEP_TMP=False

DO_SCP=True

#-------------------------------------------------------------------------------
def print_dbg(level,msg):
    now = time.strftime('%a %b %d %H:%M:%S %Y LT:')
    if level:
        print("%s %s" % (now,msg))
    return

def add_watermark(in_file, text, out_file='watermark.jpg', angle=0, opacity=0.8):
    """ add watermark text to the downloaded jpg file
    """
    img = Image.open(in_file).convert('RGB')
    watermark = Image.new('RGBA', img.size, (0,0,0,0))
    size = 2
    n_font = ImageFont.truetype(FONT, size)
    n_width, n_height = n_font.getsize(text)
    text_size_scale = 3.5
    while n_width+n_height < watermark.size[0]/text_size_scale:
        size += 2
        n_font = ImageFont.truetype(FONT, size)
        n_width, n_height = n_font.getsize(text)
    draw = ImageDraw.Draw(watermark, 'RGBA')
    draw.text(((watermark.size[0] - n_width) / 10,
               (watermark.size[1] - n_height) / 100),
    text, font=n_font, fill = (0,0,255,255))
    watermark = watermark.rotate(angle,Image.BICUBIC)
    alpha = watermark.split()[3 ]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    watermark.putalpha(alpha)
    Image.composite(watermark, img, watermark,).save(out_file, 'JPEG')


def make_gif(outgif,frames,duration,loop):
    # https://www.blog.pythonlibrary.org/2021/06/23/creating-an-animated-gif-with-python/
    frame_one = frames[0]
    frame_one.save(outgif, format="GIF", append_images=frames,
               save_all=True, duration=duration, loop=loop)


def animate_gif(in_dir,in_mask):
    """ combine the jpg files into a gif
        repeat rotation of jpgs
    """
    # get all jpg files to merge into gif
    file_names = sorted((fn for fn in os.listdir(in_dir) if fnmatch(fn,in_mask)))

    # get list of jpeg files
    images = [Image.open(in_dir + '/' + fn) for fn in file_names]

    size = (886,488)
    #size = (886/2,488/2)
    for im in images:
        im.thumbnail(size, Image.ANTIALIAS)

    print_dbg(True, "INFO: generating %s..." % outgif)
    try:
        print_dbg(DEBUG, "DEBUG: writeGif(%s,...)" % outgif)
        for n in images:
            print_dbg(DEBUG, "DEBUG: image: %s" % n)

        # 2023-11-02: it created broken gif "GIF image is corrupt (incorrect LZW compression)"
        #writeGif(outgif, images, duration=2.0, repeat=True, dither=False)
        # alternate method
        make_gif(outgif, images, duration=2000, loop=0)

    except Exception as e:
        print_dbg(True, 'ERROR: could not create %s: %s.' % (outgif,e))
        sys.exit(3)

    if not KEEP_TMP:
        for fn in file_names:
            print_dbg(True, "INFO: removing %s" % fn)
            try:
                os.remove(in_dir + fn)
            except Exception as e:
                print_dbg(True, 'ERROR: could not remove %s: %s.' % (fn,e))



def uploadGIF(gif):
    """ copies the radar gif file to the website
    """

    SCPCOMMAND_PLOTGIF = '%s -o ConnectTimeout=12 %s %s' % (SCP, gif, SCPTARGET)

    if DO_SCP:
        try:
            os.system(SCPCOMMAND_PLOTGIF)

        except Exception as e:
            print_dbg(True, 'ERROR: upload gif %s: %s.' % (gif,e))

    if not KEEP_GIF:
        if (os.path.isfile(gif)):
            os.unlink(gif)

    return

#-------------------------------------------------------------------------------

def main():
    """ download the radar images from NASA Worldview
        last NUMDAYS images. two for each day
    """
    today = datetime.combine(date.today(), datetime.min.time())

    start_date = today+timedelta(days=NUMDAYS)
    end_date   = today+timedelta(days=-1)

    # specify the dates you want to retrieve
    now = start_date

    EXTENT = "46.935791015625,13.47912597656251,49.080322265625,17.37268066406251"
    WIDTH  = "1772"
    HEIGHT = "976"

    # abort counter
    n=0
    while end_date >= now:
        year  = str(now.year)
        month = str(now.month).zfill(2)
        day   = str(now.day).zfill(2)
        dayofyear = str(now.timetuple().tm_yday).zfill(3)
        stringdate = datetime.strftime(now,"%Y-%m-%d")
        print_dbg(DEBUG, "year     : %s" % year)
        print_dbg(DEBUG, "dayofyear: %s" % dayofyear)

        print_dbg(True, "INFO: working on %s ..." % (stringdate))


        for sat in np.array(["Terra","Aqua"]):

            #URL = "https://wvs.earthdata.nasa.gov/api/v1/snapshot?REQUEST=GetSnapshot&" \
            #        "TIME="+year+"-"+month+"-"+day+"&" \
            #        "BBOX="+EXTENT+"&" \
            #        "CRS=EPSG:4326&" \
            #        "LAYERS=MODIS_"+sat+"_CorrectedReflectance_TrueColor,Coastlines,MODIS_"+sat+"_Thermal_Anomalies_All&" \
            #        "FORMAT=image/jpeg&" \
            #        "WIDTH="+WIDTH+"&HEIGHT="+HEIGHT

            URL = "https://wvs.earthdata.nasa.gov/api/v1/snapshot?REQUEST=GetSnapshot&" \
                    "TIME="+year+"-"+month+"-"+day+"&" \
                    "BBOX="+EXTENT+"&" \
                    "CRS=EPSG:4326&" \
                    "LAYERS=MODIS_"+sat+"_CorrectedReflectance_TrueColor,Reference_Labels_15m&" \
                    "FORMAT=image/jpeg&" \
                    "WIDTH="+WIDTH+"&HEIGHT="+HEIGHT

            print_dbg(DEBUG, "DEBUG: requesting: %s" % (URL))

            # Since the Terra satellite passes over before Aqua
            # we need to save it before Aqua (alphabetical order puts it in wrong order)
            if sat == "Terra":
                sat_order="1Terra"
            if sat == "Aqua":
                sat_order="2Aqua"

            image_name = 'MODIS_TrueColor_'+stringdate+'_'+ dayofyear + '_' + sat_order+'.jpg'

            if not os.path.isfile(outdir+image_name):
                try:
                    urllib.urlretrieve(URL, outdir+image_name)

                except Exception as e:
                    print_dbg(True, 'ERROR: URL: %s.' % (URL))
                    print_dbg(True, 'ERROR: could not download %s: %s.' % (image_name,e))
                    sys.exit(1)

                if imghdr.what(outdir+image_name) == 'jpeg':
                    add_watermark(outdir+image_name,sat+': '+stringdate,outdir+image_name)
                    print_dbg(True, "  " + image_name)
                else:
                    n += 1
                    print_dbg(True, 'ERROR: URL: %s.' % (URL))
                    print_dbg(True, "  %s is not a valid image file!" % image_name)
                    f    = open(outdir+image_name)
                    ftxt = f.read()
                    print(ftxt)
                    f.close()
                    if (os.path.isfile(outdir+image_name)):
                        os.unlink(outdir+image_name)

                    # abort, if too many errors occure
                    if int(n) > abs(NUMDAYS):
                        print_dbg(True, 'too many exceptions occured. Aborting...')
                        sys.exit(2)

            else:
                print_dbg(True, 'INFO: File %s already present.' % (image_name))

        now = now+timedelta(days=1)

    animate_gif(outdir,"MODIS_*")
    uploadGIF(outgif)


if __name__ == '__main__':
    main()


