#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# Name:        plotSunshine.py
# Purpose:     plot statistics about sunhine
#
#
# Configuration options in config.py
#
# depends on:  WOSPi, numpy, pandas
#
# used for:
#   WOSPi by Torkel M. Jodalen <tmj@bitwrap.no>
#   http://www.annoyingdesigns.com  -  http://www.bitwrap.no
#
# Author:      Peter Lidauer <plix1014@gmail.com>, AI
#
# Created:     30.12.2025
# Copyright:   (c) Peter Lidauer 2025
# Licence:     CC BY-NC-SA http://creativecommons.org/licenses/by-nc-sa/4.0/
# Update:
#
#-------------------------------------------------------------------------------
# Changes:

import subprocess
#from datetime import date, timedelta, datetime
from config import MYPOSITION, TMPPATH, HOMEPATH, CSVPATH, CSVFILESUFFIX, SCPTARGET, SCP
from wxtools import print_dbg, runGnuPlot, uploadPNG, uploadAny

# numpy and panda for data structure
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
from dataclasses import dataclass
import os
import time
import re
import sys
import glob
import argparse
import calendar
from typing import Dict, List, Tuple, Optional

import warnings
warnings.filterwarnings('ignore')

# current year
yy    = '%s' % time.strftime('%Y')
mm    = '%s' % time.strftime('%m')

solar_col_idx = 8
solar_threshold = 120.0

INFO  = True
DEBUG = False

# keep png files after upload
KEEP_PNG = False
# keep temporary files
KEEP_TMP = True
# upload png and inc
DO_SCP   = True


#-------------------------------------------------------------------------------

def parse_position(position_str):
    """Parse MYPOSITION string to decimal degrees"""
    position_str = position_str.upper().strip()
    
    # Pattern for: N 48*00.12'  E 016*00.101'
    pattern = r'([NS])\s*([\d.]+)[\*°]\s*([\d.]+)?\'?\s*([EW])\s*([\d.]+)[\*°]\s*([\d.]+)?\'?'
    match = re.search(pattern, position_str)
    
    if match:
        lat_dir, lat_deg, lat_min, lon_dir, lon_deg, lon_min = match.groups()
        
        lat_deg = float(lat_deg) if lat_deg else 0
        lat_min = float(lat_min) if lat_min else 0
        lon_deg = float(lon_deg) if lon_deg else 0
        lon_min = float(lon_min) if lon_min else 0
        
        latitude = lat_deg + lat_min/60.0
        if lat_dir == 'S':
            latitude = -latitude
            
        longitude = lon_deg + lon_min/60.0
        if lon_dir == 'W':
            longitude = -longitude
            
        return latitude, longitude
    
    # Default fallback
    return 48.0, 16.0

def load_and_combine_files(csv_path, year=None, month=None):
    """
    Load and combine CSV files for specific year/month or all files
    """
    if year:
        if month:
            # Specific year and month
            pattern = f"{year}-{month:02d}-{CSVFILESUFFIX}"
            print(f"Looking for files matching: {pattern}")
        else:
            # Specific year only
            pattern = f"{year}-*-{CSVFILESUFFIX}"
            print(f"Looking for files for year: {year}")
    else:
        # All files
        pattern = f"*-{CSVFILESUFFIX}"
        print(f"Looking for all available files")
    
    # Find all CSV files
    all_files = sorted(glob.glob(os.path.join(csv_path, pattern)))
    
    if not all_files:
        print(f"No CSV files found in {csv_path} with pattern {pattern}")
        return None
    
    print(f"Found {len(all_files)} CSV files:")
    
    # Load each file
    dfs = []
    for file in all_files:
        try:
            filename = os.path.basename(file)
            # Extract year-month from filename
            parts = filename.split('-')
            if len(parts) >= 2:
                file_year_month = f"{parts[0]}-{parts[1]}"
            else:
                file_year_month = filename
            
            # Read the file
            df = pd.read_csv(
                file,
                header=None,
                parse_dates=[0],
                dayfirst=True,
                infer_datetime_format=True,
                on_bad_lines='skip',
                low_memory=False
            )
            
            if len(df) > 0:
                # Ensure first column is datetime
                df[0] = pd.to_datetime(df[0], errors='coerce', dayfirst=True)
                df = df.dropna(subset=[0])  # Remove rows where datetime conversion failed
                
                if len(df) > 0:
                    dfs.append(df)
                    print(f"  ✓ {file_year_month}: {len(df):6} rows")
                else:
                    print(f"  ✗ {file_year_month}: No valid datetimes after conversion")
            else:
                print(f"  ✗ {file_year_month}: Empty file")
                
        except Exception as e:
            print(f"  ✗ {os.path.basename(file)}: Error - {e}")
    
    if not dfs:
        print("No valid data loaded!")
        return None
    
    # Combine all dataframes
    if len(dfs) == 1:
        combined_df = dfs[0]
    else:
        combined_df = pd.concat(dfs, ignore_index=True)
    
    # Ensure datetime column is properly sorted
    combined_df = combined_df.sort_values(by=0).reset_index(drop=True)
    
    print(f"\nCombined dataset: {len(combined_df):,} total rows")
    print(f"Date range: {combined_df[0].min()} to {combined_df[0].max()}")
    
    return combined_df

def get_available_years(csv_path):
    """Get list of available years in the data directory"""
    pattern = f"*-{CSVFILESUFFIX}"
    all_files = glob.glob(os.path.join(csv_path, pattern))
    
    years = set()
    for file in all_files:
        filename = os.path.basename(file)
        parts = filename.split('-')
        if len(parts) >= 1 and parts[0].isdigit():
            years.add(int(parts[0]))
    
    return sorted(years)

def analyze_solar_column(df, solar_col_idx=8):
    """
    Analyze the solar radiation column to understand the data
    """
    print("\n" + "="*60)
    print("ANALYZING SOLAR RADIATION DATA")
    print("="*60)
    
    # Rename columns for clarity
    num_cols = len(df.columns)
    col_names = [f'col_{i}' for i in range(num_cols)]
    col_names[0] = 'datetime'
    
    # Check if solar column index is valid
    if solar_col_idx >= num_cols:
        print(f"ERROR: Solar column index {solar_col_idx} is out of range.")
        print(f"DataFrame has {num_cols} columns (0-{num_cols-1})")
        print("\nAvailable columns preview:")
        for i in range(min(10, num_cols)):
            sample = df.iloc[0, i] if len(df) > 0 else "N/A"
            print(f"  Column {i}: {sample}")
        
        # Let user choose
        solar_col_idx = int(input(f"\nEnter solar column index (0-{num_cols-1}): "))
        if solar_col_idx >= num_cols:
            print("Invalid column index!")
            return None
    
    col_names[solar_col_idx] = 'solar_rad'
    df.columns = col_names
    
    # Convert solar_rad to numeric, coerce errors
    df['solar_rad'] = pd.to_numeric(df['solar_rad'], errors='coerce')
    
    # Basic statistics
    solar_stats = df['solar_rad'].describe()
    print(f"\nBasic statistics for solar radiation:")
    print(f"  Min:     {solar_stats['min']:8.1f} W/m²")
    print(f"  Max:     {solar_stats['max']:8.1f} W/m²")
    print(f"  Mean:    {solar_stats['mean']:8.1f} W/m²")
    print(f"  Std:     {solar_stats['std']:8.1f} W/m²")
    print(f"  25%:     {solar_stats['25%']:8.1f} W/m²")
    print(f"  50%:     {solar_stats['50%']:8.1f} W/m² (median)")
    print(f"  75%:     {solar_stats['75%']:8.1f} W/m²")
    
    # Count zeros and non-zeros
    total = len(df)
    zeros = (df['solar_rad'] == 0).sum()
    non_zeros = total - zeros
    print(f"\nZero vs Non-zero values:")
    print(f"  Zero values:     {zeros:8} ({zeros/total*100:5.1f}%)")
    print(f"  Non-zero values: {non_zeros:8} ({non_zeros/total*100:5.1f}%)")
    
    # Values above thresholds
    print(f"\nValues above thresholds:")
    thresholds = [1, 50, 100, 120, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    for threshold in thresholds:
        above = (df['solar_rad'] > threshold).sum()
        if above > 0:
            print(f"  >{threshold:4d} W/m²: {above:8} ({above/total*100:5.1f}%)")
    
    # Analyze by year and month
    df['year'] = df['datetime'].dt.year
    df['month'] = df['datetime'].dt.month
    
    print(f"\nYearly maximums:")
    yearly_max = df.groupby('year')['solar_rad'].max()
    for year, max_val in yearly_max.items():
        if max_val > 0:
            print(f"  {year}: {max_val:6.1f} W/m²")
    
    print(f"\nMonthly statistics (across all years in dataset):")
    monthly_stats = df.groupby('month')['solar_rad'].agg(['max', 'mean', 'count']).round(1)
    for month in range(1, 13):
        if month in monthly_stats.index:
            stats = monthly_stats.loc[month]
            month_name = datetime(2000, month, 1).strftime('%b')
            print(f"  {month_name}: max={stats['max']:5.0f}, avg={stats['mean']:5.1f}, readings={int(stats['count']):,}")
    
    # Check for diurnal pattern
    df['hour'] = df['datetime'].dt.hour
    hourly_avg = df.groupby('hour')['solar_rad'].mean()
    
    print(f"\nDiurnal pattern (average by hour):")
    for hour in range(0, 24):
        if hour in hourly_avg.index:
            print(f"  {hour:02d}:00 - {hourly_avg[hour]:6.1f} W/m²")
    
    # Check if values seem reasonable
    max_solar = df['solar_rad'].max()
    if max_solar < 500:
        print(f"\n⚠ WARNING: Maximum value ({max_solar:.1f} W/m²) seems low.")
        print("  Possible issues:")
        print("  1. Wrong column (not solar radiation)")
        print("  2. Units issue (e.g., data in kJ/m² or other units)")
        print("  3. Sensor calibration issue")
        print("  4. Heavy cloud cover entire period")
        
        # Check for unit conversion possibility
        if max_solar < 500 and max_solar > 0:
            print(f"\nPossible unit conversions (if data is actually in different units):")
            print(f"  If data is in W/m² * 0.1: {max_solar*10:.1f} W/m²")
            print(f"  If data is in kJ/m²: {max_solar*0.2778:.1f} W/m² (divide by 3.6)")
            print(f"  If data is in MJ/m²: {max_solar*277.8:.1f} W/m² (multiply by 277.8)")
    
    return df, solar_col_idx

@dataclass
class SunCalculator:
    """Class to calculate sunshine hours"""
    latitude: float = 48.0
    longitude: float = 16.0
    altitude: float = 200.0
    
    def clear_sky_radiation(self, dt: datetime) -> float:
        """Calculate clear-sky solar radiation"""
        try:
            # Day of year
            doy = dt.timetuple().tm_yday
            
            # Solar declination
            declination = 0.409 * np.sin(2 * np.pi / 365 * doy - 1.39)
            
            # Latitude in radians
            lat_rad = np.radians(self.latitude)
            
            # Hour angle
            hour = dt.hour + dt.minute / 60.0
            hour_angle = np.radians(15 * (hour - 12))
            
            # Solar zenith angle
            cos_theta = (np.sin(lat_rad) * np.sin(declination) + 
                        np.cos(lat_rad) * np.cos(declination) * np.cos(hour_angle))
            cos_theta = max(0.001, cos_theta)  # Avoid division by zero
            
            # Clear-sky radiation model
            solar_constant = 1367
            G_sc = solar_constant * (1 + 0.033 * np.cos(2 * np.pi * doy / 365))
            tau = 0.65 + 0.02 * np.exp(-self.altitude / 8000)
            
            G_clear = G_sc * cos_theta * tau ** (1 / cos_theta)
            
            return max(0, G_clear)
        except:
            return 0

def calculate_sunshine(df, latitude, longitude, solar_threshold=120, year=None):
    """
    Calculate sunshine hours from the DataFrame
    """
    if year:
        print(f"\n{'='*60}")
        print(f"CALCULATING SUNSHINE HOURS FOR {year}")
        print(f"Location: {latitude:.4f}°N, {longitude:.4f}°E")
    else:
        print(f"\n{'='*60}")
        print(f"CALCULATING SUNSHINE HOURS")
        print(f"Location: {latitude:.4f}°N, {longitude:.4f}°E")
    
    print(f"Threshold: {solar_threshold} W/m²")
    print("="*60)
    
    # Make sure we have the right columns
    if 'solar_rad' not in df.columns:
        print("ERROR: 'solar_rad' column not found in DataFrame!")
        return None, None, None
    
    # Create date columns
    df['date'] = df['datetime'].dt.date
    df['year'] = df['datetime'].dt.year
    df['month'] = df['datetime'].dt.month
    df['hour'] = df['datetime'].dt.hour
    df['minute'] = df['datetime'].dt.minute
    
    # Initialize sun calculator
    sun_calc = SunCalculator(latitude=latitude, longitude=longitude)
    
    # Calculate clear-sky radiation
    print("Calculating clear-sky radiation...", end='', flush=True)
    df['clear_sky_rad'] = df['datetime'].apply(sun_calc.clear_sky_radiation)
    print(" ✓")
    
    # Calculate time interval between readings
    df['time_diff'] = df['datetime'].diff().dt.total_seconds() / 3600.0
    if len(df) > 1:
        df.loc[0, 'time_diff'] = df.loc[1, 'time_diff']
    else:
        df.loc[0, 'time_diff'] = 0.0833  # Default 5 minutes
    
    median_interval = df['time_diff'].median()
    print(f"  Median interval: {median_interval*60:.1f} minutes")
    
    # Calculate ratio and detect sunshine
    print("Detecting sunshine intervals...", end='', flush=True)
    
    # Handle division by zero
    df['ratio'] = df['solar_rad'] / df['clear_sky_rad']
    df['ratio'] = df['ratio'].fillna(0)
    df['ratio'] = df['ratio'].replace([np.inf, -np.inf], 0)
    df['ratio'] = df['ratio'].clip(0, 2)
    
    # WMO algorithm: > threshold AND ratio > 0.4
    df['is_sunshine'] = ((df['solar_rad'] > solar_threshold) & (df['ratio'] > 0.4)).astype(int)
    df['sunshine_hours'] = df['is_sunshine'] * df['time_diff']
    
    total_sunshine_intervals = df['is_sunshine'].sum()
    total_intervals = len(df)
    print(f" ✓")
    print(f"  Sunshine detected in {total_sunshine_intervals:,} of {total_intervals:,} intervals "
          f"({total_sunshine_intervals/total_intervals*100:.1f}%)")
    
    # Determine output file names based on year
    if year:
        daily_file = f'daily_sunshine_{year}.csv'
        monthly_file = f'monthly_sunshine_{year}.csv'
        hourly_file = f'hourly_sunshine_profile_{year}.csv'
    else:
        daily_file = 'daily_sunshine_all_years.csv'
        monthly_file = 'monthly_sunshine_all_years.csv'
        hourly_file = 'hourly_sunshine_profile_all_years.csv'
    
    # DAILY SUMMARY
    print("\nCreating daily summary...", end='', flush=True)
    daily_summary = df.groupby('date').agg({
        'solar_rad': 'mean',
        'sunshine_hours': 'sum',
        'is_sunshine': 'count'
    }).reset_index()
    
    daily_summary.columns = ['date', 'avg_solar_rad', 'sunshine_hours', 'readings']
    daily_summary['sunshine_percent'] = (daily_summary['sunshine_hours'] / 
                                        (daily_summary['readings'] * median_interval)) * 100
    daily_summary['date_str'] = daily_summary['date'].astype(str)
    daily_summary['year'] = pd.to_datetime(daily_summary['date']).dt.year
    daily_summary['month'] = pd.to_datetime(daily_summary['date']).dt.month
    daily_summary['weekday'] = pd.to_datetime(daily_summary['date']).dt.day_name()
    
    daily_summary.to_csv(TMPPATH+daily_file, index=False, float_format='%.3f')
    print(f" ✓\n  Saved to: {daily_file}")
    
    # MONTHLY SUMMARY
    print("Creating monthly summary...", end='', flush=True)
    monthly_summary = daily_summary.groupby(['year', 'month']).agg({
        'sunshine_hours': 'sum',
        'avg_solar_rad': 'mean',
        'date': 'count'
    }).reset_index()
    
    monthly_summary.columns = ['year', 'month', 'total_sunshine', 'avg_solar_rad', 'days']
    monthly_summary['sunshine_per_day'] = monthly_summary['total_sunshine'] / monthly_summary['days']
    monthly_summary['month_name'] = monthly_summary['month'].apply(lambda x: date(2000, x, 1).strftime('%b'))
    monthly_summary['year_month'] = monthly_summary['year'].astype(str) + '-' + monthly_summary['month'].astype(str).str.zfill(2)
    
    monthly_summary.to_csv(TMPPATH+monthly_file, index=False, float_format='%.2f')
    print(f" ✓\n  Saved to: {monthly_file}")
    
    # HOURLY PROFILE
    print("Creating hourly profile...", end='', flush=True)
    
    # Filter daylight hours
    daylight = df[(df['hour'] >= 6) & (df['hour'] <= 20)].copy()
    hourly_profile = daylight.groupby('hour').agg({
        'is_sunshine': 'mean',
        'solar_rad': 'mean',
        'clear_sky_rad': 'mean'
    }).reset_index()
    
    hourly_profile['sunshine_prob'] = hourly_profile['is_sunshine'] * 100
    
    hourly_profile.to_csv(TMPPATH+hourly_file, index=False, float_format='%.1f')
    print(f" ✓\n  Saved to: {hourly_file}")
    
    # Print summary
    print(f"\n{'='*60}")
    if year:
        print(f"SUMMARY FOR {year}")
    else:
        print("SUMMARY (All Years)")
    print("="*60)
    
    total_days = len(daily_summary)
    total_sunshine = daily_summary['sunshine_hours'].sum()
    avg_daily = daily_summary['sunshine_hours'].mean()
    
    print(f"\nStatistics:")
    print(f"  Total days analyzed: {total_days:,}")
    print(f"  Total sunshine hours: {total_sunshine:,.1f}")
    print(f"  Average daily sunshine: {avg_daily:.2f} hours")
    print(f"  Maximum daily sunshine: {daily_summary['sunshine_hours'].max():.2f} hours")
    
    # Top sunniest days
    if len(daily_summary) >= 5:
        print(f"\nTop 5 Sunniest Days:")
        top_days = daily_summary.nlargest(5, 'sunshine_hours')
        for idx, row in top_days.iterrows():
            print(f"  {row['date']}: {row['sunshine_hours']:.2f} hours")
    
    # Monthly totals
    print(f"\nMonthly Totals:")
    for idx, row in monthly_summary.iterrows():
        print(f"  {row['year_month']} ({row['month_name']}): "
              f"{row['total_sunshine']:.1f} hours ({row['sunshine_per_day']:.2f} hours/day)")
    

    return daily_summary, monthly_summary, hourly_profile


def gnuplotStats(plt):
    """ run gnuplot
    """

    filebase = os.path.splitext(os.path.basename(plt))[0]
    pngfile  = TMPPATH + filebase+'.png'

    print_dbg(True,"INFO : plot statistics with " + plt)

    LEVEL1 = True
    LEVEL2 = True

    # full error message
    re_stderr = re.compile(r'^.*,\s+(line\s+\d+):\s+(.*)')
    el = 0

    gnuplot = '/usr/bin/gnuplot'

    if os.path.exists(gnuplot):
        print_dbg(LEVEL1,"runGnuPlot: plot png " + plt)
        try:
            proc_out = subprocess.Popen([gnuplot, plt], stdout=subprocess.PIPE,stderr=subprocess.PIPE)

            output = proc_out.stdout.readlines()
            outerr = proc_out.stderr.readlines()

            for line in outerr:
                line = line.decode('latin1').strip()
                m = re.search(re_stderr, line)
                if m:
                    print_dbg(True, "STDERR: %s" % line)
                    if re.search("warning:",line):
                        # we ignore warning errors
                        pass
                    else:
                        raise ValueError('syntax or plot error in gnuplot file')
                    el = 1

            if LEVEL2:
                for n in output:
                    print_dbg(True, "STDOUT: %s" % n.strip())
                for n in outerr:
                    print_dbg(True, "STDERR: %s" % n.strip())

        except Exception as e:
            print_dbg(True, 'WARN : GnuPlot done with exception(s): %s.' % e)
            el = 1

    else:
        print_dbg(True,"ERROR: gnuplot command '%s' not found." % gnuplot)
        el = 1

    # cleanup temp files
    #if not KEEP_TMP:
        #if (os.path.isfile(inFile)):
        #    os.unlink(inFile)

        #tmpFile = config.TMPPATH + 'plot' + plt + '.tmp'
        #if (os.path.isfile(tmpFile)):
        #    os.unlink(tmpFile)
        #else:
        #    print_dbg(LEVEL1,"tmp file not found: %s" % tmpFile)

    return el

    return


def create_year_specific_visualizations(year):
    """Create gnuplot scripts for specific year"""
    
    # Daily sunshine for specific year
    daily_script = f"""# Daily Sunshine Hours for {year}
set terminal pngcairo size 1800,600 enhanced font 'Helvetica,12'
set output '{TMPPATH}daily_sunshine_{year}.png'

set datafile separator ","
set xdata time
set timefmt "%Y-%m-%d"
#set format x "%d.%m.%Y"
set format x "%d.%m"
#set format x "%b"
set xtics rotate by -45
#set xtics rotate by 0
#set xtics rotate by -45 offset 0,-1.5 font ",9"
#set xtics 604800  # Weekly tics
set xtics 1209600  # Bi-weekly tics (2 weeks)
#set xtics 2592000  # Monthly tics (approx 30 days)
set mxtics 7
#set mxtics 4

# Adjust margins to fit rotated labels
set lmargin 10
set rmargin 4
set bmargin 8

set grid xtics ytics
set title "Daily Sunshine Hours {year}\\nLocation: {MYPOSITION}"
set ylabel "Sunshine Hours"
set xlabel "Date"
set yrange [0:*]

set style fill solid 0.7
set boxwidth 0.7 relative

# Define colors
set linetype 1 lc rgb "#FFA500"  # Orange for bars
set linetype 2 lc rgb "#FF8C00"  # Darker orange for line

plot '{TMPPATH}daily_sunshine_{year}.csv' using 1:3 with boxes lc rgb "#FFA500" title "Sunshine Hours", \\
     '' using 1:3 with lines lw 2 lc rgb "#FF8C00" notitle
"""
    
    with open(TMPPATH+f'plot_daily_{year}.gp', 'w') as f:
        f.write(daily_script)

    gnuplotStats(TMPPATH+f'plot_daily_{year}.gp')
    uploadPNG(TMPPATH  + f'daily_sunshine_{year}.png', DO_SCP, KEEP_PNG, SCP)
    if not KEEP_TMP:
        os.unlink(TMPPATH+f'plot_daily_{year}.gp')
    

    # Monthly summary for specific year
    monthly_script = f"""# Monthly Sunshine for {year}
set terminal pngcairo size 1200,700 enhanced font 'Helvetica,11'
set output '{TMPPATH}monthly_sunshine_{year}.png'

set datafile separator ","
set style data histograms
set style histogram clustered gap 1
set style fill solid 0.8 border -1
set boxwidth 0.9

# Better colors
set style fill solid border rgb "black"
set linetype 1 lc rgb "#FF8C00"  # Total hours
set linetype 2 lc rgb "#1E90FF"  # Daily average

set grid ytics lt 0 lw 1 lc rgb "#DDDDDD"
set title "Monthly Sunshine Hours {year}\\nLocation: {MYPOSITION}" font ",14"
set ylabel "Sunshine Hours" font ",12"
set yrange [0:*]

# Horizontal month labels (looks cleaner for 12 items)
set xtics rotate by 0 font ",11"
unset xlabel  # Months are obvious

# Optional: Add value labels on top of bars
set label at graph 0,1.05 "{MYPOSITION}" font ",10" center

plot '{TMPPATH}monthly_sunshine_{year}.csv' using 3:xtic(7) title "Total Sunshine", \
     '' using 4 title "Avg Solar Radiation"
"""
    
    with open(TMPPATH+f'plot_monthly_{year}.gp', 'w') as f:
        f.write(monthly_script)

    gnuplotStats(TMPPATH+f'plot_monthly_{year}.gp')
    uploadPNG(TMPPATH  + f'monthly_sunshine_{year}.png', DO_SCP, KEEP_PNG, SCP)
    if not KEEP_TMP:
        os.unlink(TMPPATH+f'plot_monthly_{year}.gp')
    
    print(f"\nCreated gnuplot scripts for {year}:")
    print(f"  plot_daily_{year}.gp")
    print(f"  plot_monthly_{year}.gp")
    #print(f"\nTo generate charts for {year}:")
    #print(f"  gnuplot plot_daily_{year}.gp")
    #print(f"  gnuplot plot_monthly_{year}.gp")



#######################################################################################################
#---- from sunshine_statistics.py ---------------------------------------------------------------------------

def generate_sunshine_statistics(year: int, output_file: str = None) -> str:
    """
    Generate sunshine statistics HTML table for a specific year
    Returns HTML table as string and saves to file if output_file is provided
    """
    
    # Load the sunshine data for the year
    daily_file = TMPPATH+f'daily_sunshine_{year}.csv'
    monthly_file = TMPPATH+f'monthly_sunshine_{year}.csv'
    
    if not os.path.exists(daily_file) or not os.path.exists(monthly_file):
        print(f"Error: Sunshine data files for {year} not found!")
        print(f"Please run sunshine analysis for {year} first.")
        return ""
    
    # Load data
    daily = pd.read_csv(daily_file)
    monthly = pd.read_csv(monthly_file)
    
    # Convert dates
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily['month'] = daily['date'].dt.month
    daily['day'] = daily['date'].dt.day
    
    # Calculate additional statistics
    monthly_stats = calculate_monthly_statistics(daily, monthly)
    yearly_stats = calculate_yearly_statistics(daily, monthly)
    
    # Generate HTML table
    html_table = create_html_table(monthly_stats, yearly_stats, year)
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_table)
        print(f"Sunshine statistics saved to: {output_file}")
    
    return html_table

def calculate_monthly_statistics(daily_df: pd.DataFrame, monthly_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate detailed monthly statistics"""
    
    # Group by month
    monthly_stats = daily_df.groupby('month').agg({
        'sunshine_hours': ['sum', 'mean', 'max', 'min', 'std'],
        'avg_solar_rad': 'mean',
        'date': 'count'
    }).round(2)
    
    # Flatten column names
    monthly_stats.columns = [
        'total_sunshine', 'avg_sunshine', 'max_daily', 'min_daily', 
        'std_sunshine', 'avg_radiation', 'days'
    ]
    
    # Calculate additional metrics
    monthly_stats['sunny_days'] = daily_df[daily_df['sunshine_hours'] > 0].groupby('month').size()
    monthly_stats['sunny_days'] = monthly_stats['sunny_days'].fillna(0).astype(int)
    
    # Calculate days with more than X hours of sunshine
    thresholds = [1, 3, 5, 8, 10]
    for threshold in thresholds:
        col_name = f'days_>{threshold}h'
        monthly_stats[col_name] = daily_df[daily_df['sunshine_hours'] > threshold].groupby('month').size()
        monthly_stats[col_name] = monthly_stats[col_name].fillna(0).astype(int)
    
    # Calculate percentage of possible sunshine
    monthly_stats['sunshine_percent'] = (monthly_stats['total_sunshine'] / 
                                        (monthly_stats['days'] * 24)) * 100
    
    # Add month names
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    monthly_stats['month_name'] = monthly_stats.index.map(month_names)
    
    # Reorder columns
    columns_order = ['month_name', 'days', 'total_sunshine', 'avg_sunshine', 
                     'max_daily', 'min_daily', 'sunny_days', 'days_>1h',
                     'days_>3h', 'days_>5h', 'days_>8h', 'sunshine_percent',
                     'avg_radiation', 'std_sunshine']
    
    # Only include columns that exist
    available_columns = [col for col in columns_order if col in monthly_stats.columns]
    monthly_stats = monthly_stats[available_columns]
    
    return monthly_stats

def calculate_yearly_statistics(daily_df: pd.DataFrame, monthly_df: pd.DataFrame) -> Dict:
    """Calculate yearly statistics"""
    
    yearly_stats = {
        'total_sunshine': daily_df['sunshine_hours'].sum(),
        'avg_daily_sunshine': daily_df['sunshine_hours'].mean(),
        'max_daily_sunshine': daily_df['sunshine_hours'].max(),
        'min_daily_sunshine': daily_df['sunshine_hours'].min(),
        'std_daily_sunshine': daily_df['sunshine_hours'].std(),
        'avg_radiation': daily_df['avg_solar_rad'].mean(),
        'total_days': len(daily_df),
        'sunny_days': (daily_df['sunshine_hours'] > 0).sum(),
        'days_gt_1h': (daily_df['sunshine_hours'] > 1).sum(),
        'days_gt_3h': (daily_df['sunshine_hours'] > 3).sum(),
        'days_gt_5h': (daily_df['sunshine_hours'] > 5).sum(),
        'days_gt_8h': (daily_df['sunshine_hours'] > 8).sum(),
        'sunshine_percent': (daily_df['sunshine_hours'].sum() / (len(daily_df) * 24)) * 100,
        'sunniest_month': monthly_df.loc[monthly_df['total_sunshine'].idxmax(), 'month_name'],
        'sunniest_month_hours': monthly_df['total_sunshine'].max(),
        'least_sunny_month': monthly_df.loc[monthly_df['total_sunshine'].idxmin(), 'month_name'],
        'least_sunny_month_hours': monthly_df['total_sunshine'].min(),
        'sunniest_day': daily_df.loc[daily_df['sunshine_hours'].idxmax(), 'date_str'],
        'sunniest_day_hours': daily_df['sunshine_hours'].max(),
        'longest_sunny_streak': calculate_longest_streak(daily_df, 'sunshine_hours', '>', 0),
        'longest_sunless_streak': calculate_longest_streak(daily_df, 'sunshine_hours', '=', 0)
    }
    
    # Round numeric values
    for key in yearly_stats:
        if isinstance(yearly_stats[key], (float, np.float64)):
            yearly_stats[key] = round(yearly_stats[key], 2)
    
    return yearly_stats

def calculate_longest_streak(df: pd.DataFrame, column: str, condition: str, value: float) -> int:
    """Calculate longest streak of days meeting a condition"""
    if condition == '>':
        mask = df[column] > value
    elif condition == '>=':
        mask = df[column] >= value
    elif condition == '==':
        mask = df[column] == value
    elif condition == '<':
        mask = df[column] < value
    elif condition == '<=':
        mask = df[column] <= value
    else:
        return 0
    
    # Find streaks
    streak = 0
    max_streak = 0
    for val in mask:
        if val:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    
    return max_streak

def create_html_table(monthly_stats: pd.DataFrame, yearly_stats: Dict, year: int) -> str:
    """Create HTML table similar to your temperature statistics"""
    
    # Create month abbreviations list
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Build HTML table
    html = f"""<table class="dataframe df">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Total Sunshine</th>
      <th>Avg Daily</th>
      <th>Max Daily</th>
      <th>Min Daily</th>
      <th>Sunny Days</th>
      <th>Days >1h</th>
      <th>Days >3h</th>
      <th>Days >5h</th>
      <th>Sunshine %</th>
      <th>Avg Radiation</th>
    </tr>
  </thead>
  <tbody>
"""
    
    # Add monthly data
    for month_name in months:
        if month_name in monthly_stats['month_name'].values:
            month_data = monthly_stats[monthly_stats['month_name'] == month_name].iloc[0]
            
            html += f"""    <tr>
      <th>{month_name}</th>
      <td>{month_data.get('total_sunshine', 0):.1f}</td>
      <td>{month_data.get('avg_sunshine', 0):.2f}</td>
      <td>{month_data.get('max_daily', 0):.2f}</td>
      <td>{month_data.get('min_daily', 0):.2f}</td>
      <td>{month_data.get('sunny_days', 0)}</td>
      <td>{month_data.get('days_>1h', 0)}</td>
      <td>{month_data.get('days_>3h', 0)}</td>
      <td>{month_data.get('days_>5h', 0)}</td>
      <td>{month_data.get('sunshine_percent', 0):.1f}</td>
      <td>{month_data.get('avg_radiation', 0):.1f}</td>
    </tr>
"""
    
    # Add yearly summary row
    html += f"""    <tr>
      <th>{year}</th>
      <td>{yearly_stats['total_sunshine']:.1f}</td>
      <td>{yearly_stats['avg_daily_sunshine']:.2f}</td>
      <td>{yearly_stats['max_daily_sunshine']:.2f}</td>
      <td>{yearly_stats['min_daily_sunshine']:.2f}</td>
      <td>{yearly_stats['sunny_days']}</td>
      <td>{yearly_stats['days_gt_1h']}</td>
      <td>{yearly_stats['days_gt_3h']}</td>
      <td>{yearly_stats['days_gt_5h']}</td>
      <td>{yearly_stats['sunshine_percent']:.1f}</td>
      <td>{yearly_stats['avg_radiation']:.1f}</td>
    </tr>
"""
    
    html += """  </tbody>
</table>
"""
    
    return html

def create_detailed_report(year: int, output_dir: str = '.') -> str:
    """
    Create a comprehensive sunshine report with multiple tables
    """
    
    # Load data
    daily_file = TMPPATH+f'daily_sunshine_{year}.csv'
    monthly_file = TMPPATH+f'monthly_sunshine_{year}.csv'
    
    if not os.path.exists(daily_file) or not os.path.exists(monthly_file):
        return ""
    
    daily = pd.read_csv(daily_file)
    monthly = pd.read_csv(monthly_file)
    
    # Convert dates
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily['month'] = daily['date'].dt.month
    
    # Calculate statistics
    monthly_stats = calculate_monthly_statistics(daily, monthly)
    yearly_stats = calculate_yearly_statistics(daily, monthly)
    
    # Create detailed HTML report
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunshine Statistics {year} - {MYPOSITION}</title>
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; margin-top: 1.5em; }}
        h1 {{ border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 0.95em; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
        th {{ background-color: #4CAF50; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .highlight {{ background-color: #fffacd; }}
        .summary-box {{ 
            border: 2px solid #4CAF50; 
            padding: 20px; 
            margin: 25px 0; 
            background-color: #f9fff9;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-value {{ font-weight: bold; color: #2E8B57; font-size: 1.1em; }}
        .month-stats {{ 
            page-break-inside: avoid; 
            margin: 25px 0;
        }}
        .category-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .category-card {{
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background-color: #f8f9fa;
        }}
        .category-card h4 {{
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        .no-print {{ 
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 30px;
            border-left: 4px solid #3498db;
        }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ font-size: 11pt; margin: 0.5in; }}
            table {{ font-size: 10pt; }}
            .summary-box {{ border: 1px solid #000; box-shadow: none; }}
        }}
        @media (max-width: 768px) {{
            table {{ display: block; overflow-x: auto; }}
            .category-grid {{ grid-template-columns: 1fr; }}
        }}
        .month-name {{
            color: #2c3e50;
            background-color: #e8f4f8;
            padding: 8px 12px;
            border-radius: 4px;
            margin: 15px 0 10px 0;
            border-left: 4px solid #3498db;
        }}
        .data-label {{ font-weight: 600; color: #555; }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>☀️ Sunshine Statistics {year}</h1>
    <p><strong>📍 Location:</strong> {MYPOSITION}</p>
    <p><strong>📅 Analysis Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>📊 WMO Sunshine Definition:</strong> Solar radiation > 120 W/m² with clear-sky ratio > 0.4</p>
    
    <div class="summary-box">
        <h2>📈 Yearly Summary</h2>
        <table>
            <tr>
                <td class="data-label">Total Sunshine Hours:</td>
                <td class="stat-value">{yearly_stats['total_sunshine']:.1f} h</td>
                <td class="data-label">Average Daily Sunshine:</td>
                <td class="stat-value">{yearly_stats['avg_daily_sunshine']:.2f} h</td>
            </tr>
            <tr>
                <td class="data-label">Sunniest Day:</td>
                <td class="stat-value">{yearly_stats['sunniest_day']} ({yearly_stats['sunniest_day_hours']:.2f} h)</td>
                <td class="data-label">Sunniest Month:</td>
                <td class="stat-value">{yearly_stats['sunniest_month']} ({yearly_stats['sunniest_month_hours']:.1f} h)</td>
            </tr>
            <tr>
                <td class="data-label">Least Sunny Month:</td>
                <td class="stat-value">{yearly_stats['least_sunny_month']} ({yearly_stats['least_sunny_month_hours']:.1f} h)</td>
                <td class="data-label">Sunshine Percentage:</td>
                <td class="stat-value">{yearly_stats['sunshine_percent']:.1f}%</td>
            </tr>
            <tr>
                <td class="data-label">Longest Sunny Streak:</td>
                <td class="stat-value">{yearly_stats['longest_sunny_streak']} days</td>
                <td class="data-label">Longest Sunless Streak:</td>
                <td class="stat-value">{yearly_stats['longest_sunless_streak']} days</td>
            </tr>
            <tr>
                <td class="data-label">Sunny Days (any sunshine):</td>
                <td class="stat-value">{yearly_stats['sunny_days']} days</td>
                <td class="data-label">Days with >5h Sunshine:</td>
                <td class="stat-value">{yearly_stats['days_gt_5h']} days</td>
            </tr>
        </table>
    </div>
    
    <h2>📅 Monthly Sunshine Statistics</h2>
    <p><em>Comprehensive monthly breakdown of sunshine hours and statistics</em></p>
"""
    
    # Add monthly statistics table
    html += create_html_table(monthly_stats, yearly_stats, year)
    
    # Add monthly details
    html += """
    <h2>📊 Monthly Details</h2>
    <p><em>Detailed statistics for each month</em></p>
    <div class="month-stats">
"""
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for month_name in months:
        if month_name in monthly_stats['month_name'].values:
            month_data = monthly_stats[monthly_stats['month_name'] == month_name].iloc[0]
            monthly_total = monthly[monthly['month_name'] == month_name]
            
            if not monthly_total.empty:
                month_total_hours = monthly_total.iloc[0]['total_sunshine']
                month_avg_daily = monthly_total.iloc[0]['sunshine_per_day']
                month_days = month_data.get('days', 30)
                
                html += f"""
        <div class="month-name">{month_name}</div>
        <div class="category-card">
            <table style="width: 100%;">
                <tr>
                    <td class="data-label">Total Sunshine:</td>
                    <td class="stat-value">{month_total_hours:.1f} hours</td>
                    <td class="data-label">Average per Day:</td>
                    <td class="stat-value">{month_avg_daily:.2f} hours</td>
                </tr>
                <tr>
                    <td class="data-label">Sunny Days:</td>
                    <td class="stat-value">{month_data.get('sunny_days', 0)} of {month_days} days</td>
                    <td class="data-label">Days with >5h Sunshine:</td>
                    <td class="stat-value">{month_data.get('days_>5h', 0)} days</td>
                </tr>
                <tr>
                    <td class="data-label">Sunshine Percentage:</td>
                    <td class="stat-value">{month_data.get('sunshine_percent', 0):.1f}%</td>
                    <td class="data-label">Avg Solar Radiation:</td>
                    <td class="stat-value">{month_data.get('avg_radiation', 0):.1f} W/m²</td>
                </tr>
                <tr>
                    <td class="data-label">Maximum Daily Sunshine:</td>
                    <td class="stat-value">{month_data.get('max_daily', 0):.2f} hours</td>
                    <td class="data-label">Minimum Daily Sunshine:</td>
                    <td class="stat-value">{month_data.get('min_daily', 0):.2f} hours</td>
                </tr>
            </table>
        </div>
"""
    
    html += """
    </div>
    
    <h2>🌤️ Sunshine Categories</h2>
    <p><em>Distribution of days by sunshine duration categories</em></p>
    
    <div class="category-grid">
"""
    
    # Calculate days by category
    categories = [
        ("☁️ Sunless", "0 hours", (daily['sunshine_hours'] == 0).sum(), "#a9a9a9"),
        ("⛅ Very Cloudy", "0-1 hours", ((daily['sunshine_hours'] > 0) & (daily['sunshine_hours'] <= 1)).sum(), "#87ceeb"),
        ("🌥️ Cloudy", "1-3 hours", ((daily['sunshine_hours'] > 1) & (daily['sunshine_hours'] <= 3)).sum(), "#add8e6"),
        ("🌤️ Partly Sunny", "3-5 hours", ((daily['sunshine_hours'] > 3) & (daily['sunshine_hours'] <= 5)).sum(), "#ffd700"),
        ("☀️ Sunny", "5-8 hours", ((daily['sunshine_hours'] > 5) & (daily['sunshine_hours'] <= 8)).sum(), "#ff8c00"),
        ("🔥 Very Sunny", ">8 hours", (daily['sunshine_hours'] > 8).sum(), "#ff4500")
    ]
    
    total_days = len(daily)
    for category, definition, count, color in categories:
        percentage = (count / total_days) * 100
        
        # Create a simple bar visualization
        bar_width = min(percentage * 2, 100)  # Scale for visual effect
        
        html += f"""
        <div class="category-card">
            <h4>{category}</h4>
            <p><strong>Definition:</strong> {definition} of sunshine</p>
            <p><strong>Days:</strong> {count} days</p>
            <p><strong>Percentage:</strong> {percentage:.1f}%</p>
            <div style="margin-top: 10px; height: 10px; background-color: #eee; border-radius: 5px;">
                <div style="height: 100%; width: {bar_width}%; background-color: {color}; border-radius: 5px;"></div>
            </div>
        </div>
"""
    
    html += """
    </div>
    
    <h2>📋 Summary Table</h2>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Definition</th>
                <th>Days</th>
                <th>Percentage</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for category, definition, count, _ in categories:
        percentage = (count / total_days) * 100
        html += f"""
            <tr>
                <td>{category}</td>
                <td>{definition}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
"""
    
    html += f"""
            <tr style="font-weight: bold; background-color: #f0f8ff;">
                <td>Total</td>
                <td>All days</td>
                <td>{total_days}</td>
                <td>100.0%</td>
            </tr>
        </tbody>
    </table>
    
    <h2>📊 Key Statistics</h2>
    <div class="category-grid">
        <div class="category-card">
            <h4>📈 Annual Totals</h4>
            <p><span class="data-label">Total Sunshine:</span> <span class="stat-value">{yearly_stats['total_sunshine']:.1f} hours</span></p>
            <p><span class="data-label">Average per Day:</span> <span class="stat-value">{yearly_stats['avg_daily_sunshine']:.2f} hours</span></p>
            <p><span class="data-label">Sunshine Percentage:</span> <span class="stat-value">{yearly_stats['sunshine_percent']:.1f}%</span></p>
        </div>
        
        <div class="category-card">
            <h4>🏆 Records</h4>
            <p><span class="data-label">Sunniest Day:</span> <span class="stat-value">{yearly_stats['sunniest_day_hours']:.2f} h</span><br>
               <small>{yearly_stats['sunniest_day']}</small></p>
            <p><span class="data-label">Sunniest Month:</span> <span class="stat-value">{yearly_stats['sunniest_month']}</span><br>
               <small>{yearly_stats['sunniest_month_hours']:.1f} hours total</small></p>
        </div>
        
        <div class="category-card">
            <h4>⏱️ Streaks</h4>
            <p><span class="data-label">Longest Sunny Streak:</span> <span class="stat-value">{yearly_stats['longest_sunny_streak']} days</span></p>
            <p><span class="data-label">Longest Sunless Streak:</span> <span class="stat-value">{yearly_stats['longest_sunless_streak']} days</span></p>
            <p><span class="data-label">Days with any Sunshine:</span> <span class="stat-value">{yearly_stats['sunny_days']} days</span></p>
        </div>
        
        <div class="category-card">
            <h4>☀️ Quality Days</h4>
            <p><span class="data-label">Days >1h Sunshine:</span> <span class="stat-value">{yearly_stats['days_gt_1h']} days</span></p>
            <p><span class="data-label">Days >3h Sunshine:</span> <span class="stat-value">{yearly_stats['days_gt_3h']} days</span></p>
            <p><span class="data-label">Days >5h Sunshine:</span> <span class="stat-value">{yearly_stats['days_gt_5h']} days</span></p>
        </div>
    </div>
    
    <div class="no-print">
        <h3>📄 Report Information</h3>
        <p><strong>Data Source:</strong> Davis Vantage Pro2 weather station with solar radiation sensor</p>
        <p><strong>Analysis Method:</strong> WMO (World Meteorological Organization) sunshine definition</p>
        <p><strong>Calculation:</strong> Sunshine is recorded when direct solar irradiance exceeds 120 W/m²</p>
        <p><strong>Location Coordinates:</strong> {MYPOSITION}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</p>
        
        <h3>🔍 How to Read This Report</h3>
        <ul>
            <li><strong>Sunshine Hours:</strong> Total duration when the sun was shining (WMO definition)</li>
            <li><strong>Sunshine Percentage:</strong> Percentage of possible daylight hours with sunshine</li>
            <li><strong>Sunny Days:</strong> Days with at least some recorded sunshine</li>
            <li><strong>Solar Radiation:</strong> Measured in watts per square meter (W/m²)</li>
            <li><strong>Clear-Sky Radiation:</strong> Theoretical maximum radiation under ideal conditions</li>
        </ul>
    </div>
    
    <footer>
        <p>Report generated by <strong>Davis Vantage Pro2 Sunshine Analyzer</strong></p>
        <p>WMO Sunshine Definition: Direct solar irradiance > 120 W/m² with clear-sky ratio > 0.4</p>
        <p>© {datetime.now().year} Weather Station Analysis | Data from {MYPOSITION}</p>
    </footer>
</body>
</html>
"""
    
    # Save report
    report_file = os.path.join(output_dir, f'sunshine_report_{year}.html')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Detailed report saved to: {report_file}")
    
    return html

def create_combined_statistics(years: List[int], output_file: str = 'sunshine_statistics_all.inc') -> str:
    """
    Create combined statistics table for multiple years
    """
    
    all_yearly_stats = []
    
    for year in years:
        daily_file = TMPPATH+f'daily_sunshine_{year}.csv'
        monthly_file = TMPPATH+f'monthly_sunshine_{year}.csv'
        
        if os.path.exists(daily_file) and os.path.exists(monthly_file):
            daily = pd.read_csv(daily_file)
            monthly = pd.read_csv(monthly_file)
            
            yearly_stats = calculate_yearly_statistics(daily, monthly)
            yearly_stats['year'] = year
            all_yearly_stats.append(yearly_stats)
    
    if not all_yearly_stats:
        print("No yearly data found!")
        return ""
    
    # Create DataFrame
    df = pd.DataFrame(all_yearly_stats)
    
    # Create HTML table
    html = """<table class="dataframe df">
  <thead>
    <tr style="text-align: right;">
      <th>Year</th>
      <th>Total Sunshine</th>
      <th>Avg Daily</th>
      <th>Max Daily</th>
      <th>Sunny Days</th>
      <th>Days >5h</th>
      <th>Sunshine %</th>
      <th>Sunniest Month</th>
      <th>Longest Streak</th>
    </tr>
  </thead>
  <tbody>
"""
    
    for _, row in df.iterrows():
        html += f"""    <tr>
      <th>{int(row['year'])}</th>
      <td>{row['total_sunshine']:.1f}</td>
      <td>{row['avg_daily_sunshine']:.2f}</td>
      <td>{row['max_daily_sunshine']:.2f}</td>
      <td>{int(row['sunny_days'])}</td>
      <td>{int(row['days_gt_5h'])}</td>
      <td>{row['sunshine_percent']:.1f}</td>
      <td>{row['sunniest_month']}</td>
      <td>{int(row['longest_sunny_streak'])}</td>
    </tr>
"""
    
    # Add averages row
    html += """    <tr>
      <th>Average</th>
"""
    
    avg_cols = ['total_sunshine', 'avg_daily_sunshine', 'max_daily_sunshine', 
                'sunny_days', 'days_gt_5h', 'sunshine_percent', 'longest_sunny_streak']
    
    for col in avg_cols:
        if col in ['sunny_days', 'days_gt_5h', 'longest_sunny_streak']:
            value = f"{df[col].mean():.1f}"
        else:
            value = f"{df[col].mean():.2f}"
        html += f"      <td>{value}</td>\n"
    
    html += """      <td>-</td>
    </tr>
"""
    
    html += """  </tbody>
</table>
"""
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Combined statistics saved to: {output_file}")
    
    return html

#-------------------------------------------------------------------------------

def main_statistics(year):
    """Main function to generate sunshine statistics"""
    
    print("\n" + "="*60)
    print("SUNSHINE STATISTICS GENERATOR")
    print("="*60)
    
    
    print(f"\nGenerating sunshine statistics for {year}...")
    print(f"Location: {MYPOSITION}")
    
    # Check if data exists
    daily_file = TMPPATH+f'daily_sunshine_{year}.csv'
    if not os.path.exists(daily_file):
        print(f"\nError: Sunshine data for {year} not found!")
        print(f"Please run sunshine analysis for {year} first.")
        print(f"Expected file: {daily_file}")
        return
    
    # Create output directory
    #output_dir = 'sunshine_statistics'
    output_dir = TMPPATH
    #os.makedirs(output_dir, exist_ok=True)
    
    # 1. Generate simple HTML table (like your temperature stats)
    simple_html = generate_sunshine_statistics(
        year, 
        output_file=os.path.join(output_dir, f'{year}.sunshine.inc')
    )
    
    if simple_html:
        print(f"\n✓ Simple statistics table generated")
        print(f"  File: {output_dir}{year}.sunshine.inc")
        uploadAny(TMPPATH  + f'{year}.sunshine.inc', DO_SCP, KEEP_PNG, SCP)
    
    # 2. Generate detailed HTML report
    detailed_report = create_detailed_report(
        year,
        output_dir=output_dir
    )

    if detailed_report:
        print(f"✓ Detailed report generated")
        print(f"  File: {output_dir}sunshine_report_{year}.html")
        uploadAny(TMPPATH  + f'sunshine_report_{year}.html', DO_SCP, KEEP_PNG, SCP)

    # 3. Ask about combined statistics
    if os.path.exists(output_dir + 'daily_sunshine_all_years.csv'):
        #create_combined = input("\nCreate combined statistics for all years? (y/n): ").strip().lower()
        create_combined = 'y'
        if create_combined == 'y':
            # Find all available years
            available_years = []
            for file in os.listdir(output_dir):
                if file.startswith('daily_sunshine_') and file.endswith('.csv'):
                    try:
                        year_str = file.replace('daily_sunshine_', '').replace('.csv', '')
                        if year_str.isdigit():
                            available_years.append(int(year_str))
                    except:
                        pass

            if available_years:
                combined_html = create_combined_statistics(
                    sorted(available_years),
                    output_file=os.path.join(output_dir, 'sunshine_statistics_all.inc')
                )
                print(f"✓ Combined statistics generated for {len(available_years)} years")
                uploadAny(TMPPATH  + f'sunshine_statistics_all.inc', DO_SCP, KEEP_PNG, SCP)


    # 4. Sunshine categories
    print(" Creating sunshine categories chart...")

    # Define categories
    categories = [
        ("0h", 0, 0),
        ("0-1h", 0, 1),
        ("1-3h", 1, 3),
        ("3-5h", 3, 5),
        ("5-8h", 5, 8),
        (">8h", 8, float('inf'))
    ]

    daily = pd.read_csv(daily_file)

    counts = []
    labels = []
    for label, low, high in categories:
        if high == float('inf'):
            count = (daily['sunshine_hours'] > low).sum()
        else:
            count = ((daily['sunshine_hours'] >= low) & 
                    (daily['sunshine_hours'] < high)).sum()
        counts.append(count)
        labels.append(label)

    plt.figure(figsize=(10, 6))
    colors = plt.cm.YlOrRd(np.linspace(0.3, 0.9, len(categories)))
    plt.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%',
            startangle=90, wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    plt.title(f'Sunshine Duration Categories - {year}')
    plt.tight_layout()
    plt.savefig(TMPPATH+f'sunshine_categories_{year}.png', dpi=150)
    plt.close()
    print(f"   Saved: sunshine_categories_{year}.png")
    uploadPNG(TMPPATH  + f'sunshine_categories_{year}.png', DO_SCP, KEEP_PNG, SCP)


    print(f"\n{'='*60}")
    print("STATISTICS GENERATION COMPLETE")
    print("="*60)
    print(f"\nGenerated files in '{output_dir}' directory:")
    for file in os.listdir(output_dir):
        if str(year) in file or 'all' in file:
            print(f"  - {file}")

    print(f"\nTo include in your shtml file, add:")
    print(f'  <!--#include virtual="sunshine_statistics/{year}.sunshine.inc" -->')

#---- from sunshine_statistics.py ---------------------------------------------------------------------------

#######################################################################################################

#---- from advanced_visualizations.py ---------------------------------------------------------------------------

def create_all_visualizations():
    """Create all advanced visualizations for multi-year data"""

    # Check if files exist
    required_files = [
        'daily_sunshine_all_years.csv',
        'monthly_sunshine_all_years.csv'
    ]

    for file in required_files:
        if not os.path.exists(TMPPATH+file):
            print(f"Error: Required file '{file}' not found.")
            print("Please run the main analysis with option 2 (all years) first.")
            return

    print("Creating advanced visualizations...")

    # Load data
    daily = pd.read_csv(TMPPATH+'daily_sunshine_all_years.csv')
    monthly = pd.read_csv(TMPPATH+'monthly_sunshine_all_years.csv')

    # Convert date columns
    daily['date'] = pd.to_datetime(daily['date_str'])
    daily['year'] = daily['date'].dt.year
    daily['month'] = daily['date'].dt.month

    # 1. Monthly Heatmap
    print("1. Creating monthly heatmap...")
    plt.figure(figsize=(14, 10))

    # Pivot table for heatmap
    heatmap_data = monthly.pivot_table(values='total_sunshine', 
                                       index='year', 
                                       columns='month', 
                                       aggfunc='sum')
    
    # Fill missing months with NaN
    all_months = range(1, 13)
    all_years = range(int(heatmap_data.index.min()), int(heatmap_data.index.max()) + 1)
    heatmap_data = heatmap_data.reindex(index=all_years, columns=all_months)
    
    # Create heatmap
    plt.imshow(heatmap_data.values, cmap='YlOrRd', aspect='auto', interpolation='nearest')
    plt.colorbar(label='Sunshine Hours')
    
    # Labels
    plt.xlabel('Month')
    plt.ylabel('Year')
    plt.title(f'Monthly Sunshine Hours Heatmap\n{MYPOSITION}')
    
    # Tick labels
    plt.xticks(range(12), [calendar.month_abbr[i] for i in range(1, 13)])
    plt.yticks(range(len(all_years)), all_years)
    
    plt.tight_layout()
    plt.savefig(TMPPATH+'monthly_heatmap.png', dpi=150)
    print("   Saved: monthly_heatmap.png")
    uploadPNG(TMPPATH  + f'monthly_heatmap.png', DO_SCP, KEEP_PNG, SCP)
    
    # 2. Yearly Trends
    print("2. Creating yearly trends...")
    
    # Calculate yearly totals
    yearly_totals = daily.groupby('year')['sunshine_hours'].sum().reset_index()
    
    plt.figure(figsize=(12, 6))
    years = yearly_totals['year']
    sunshine = yearly_totals['sunshine_hours']
    
    plt.plot(years, sunshine, 'o-', linewidth=2, markersize=8, color='orange')
    plt.fill_between(years, sunshine, alpha=0.3, color='orange')
    
    # Add trend line
    if len(years) > 1:
        z = np.polyfit(years, sunshine, 1)
        p = np.poly1d(z)
        plt.plot(years, p(years), 'r--', linewidth=2, 
                label=f'Trend: {p[1]:+.1f} hours/year')
    
    plt.title(f'Yearly Sunshine Totals\n{MYPOSITION}')
    plt.xlabel('Year')
    plt.ylabel('Total Sunshine Hours')
    plt.grid(True, alpha=0.3)
    if len(years) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(TMPPATH+'yearly_trends.png', dpi=150)
    print("   Saved: yearly_trends.png")
    uploadPNG(TMPPATH  + f'yearly_trends.png', DO_SCP, KEEP_PNG, SCP)
    
    # 3. Monthly Averages across years
    print("3. Creating monthly averages...")
    plt.figure(figsize=(12, 6))
    
    # Calculate monthly averages
    monthly_avg = daily.groupby('month')['sunshine_hours'].mean()
    monthly_std = daily.groupby('month')['sunshine_hours'].std()
    
    months = range(1, 13)
    month_names = [calendar.month_abbr[i] for i in months]
    
    plt.bar(months, monthly_avg.values, yerr=monthly_std.values, 
            color='orange', alpha=0.7, capsize=5)
    plt.title(f'Average Monthly Sunshine Hours\n{MYPOSITION}')
    plt.xlabel('Month')
    plt.ylabel('Sunshine Hours per Day')
    plt.xticks(months, month_names)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(TMPPATH+'monthly_averages.png', dpi=150)
    print("   Saved: monthly_averages.png")
    uploadPNG(TMPPATH  + f'monthly_averages.png', DO_SCP, KEEP_PNG, SCP)
    
############################# old #################################################
    ## 4. Distribution of daily sunshine hours
    #print("4. Creating distribution plot...")
    #plt.figure(figsize=(12, 6))
    
    ## Create histogram
    #plt.hist(daily['sunshine_hours'], bins=50, color='orange', 
    #         alpha=0.7, edgecolor='black', density=True)
    
    ## Add kernel density estimate
    #from scipy import stats
    #kde = stats.gaussian_kde(daily['sunshine_hours'])
    #x_range = np.linspace(0, daily['sunshine_hours'].max(), 1000)
    #plt.plot(x_range, kde(x_range), 'r-', linewidth=2, label='Density')
    
    #plt.title(f'Distribution of Daily Sunshine Hours\n{MYPOSITION}')
    #plt.xlabel('Sunshine Hours per Day')
    #plt.ylabel('Density')
    #plt.grid(True, alpha=0.3)
    #plt.legend()
    #plt.tight_layout()
    #plt.savefig(TMPPATH+'sunshine_distribution.png', dpi=150)
    #print("   Saved: sunshine_distribution.png")
    #uploadPNG(TMPPATH  + f'sunshine_distribution.png', DO_SCP, KEEP_PNG, SCP)
############################# old/new #################################################

    # 4. Distribution of daily sunshine hours
    print("4. Creating distribution plot...")
    plt.figure(figsize=(12, 6))

    # Create histogram without KDE
    counts, bins, patches = plt.hist(daily['sunshine_hours'], bins=50, 
                                     color='orange', alpha=0.7, 
                                     edgecolor='black', density=True)

    # Add a simple curve using numpy instead of scipy
    # Calculate bin centers
    bin_centers = 0.5 * (bins[1:] + bins[:-1])

    # Calculate cumulative distribution for reference
    sorted_hours = np.sort(daily['sunshine_hours'])
    cumulative = np.arange(1, len(sorted_hours) + 1) / len(sorted_hours)

    # Create subplot for cumulative distribution
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Histogram on top
    ax1.hist(daily['sunshine_hours'], bins=50, color='orange', 
             alpha=0.7, edgecolor='black', density=True)
    ax1.set_title(f'Distribution of Daily Sunshine Hours\n{MYPOSITION}')
    ax1.set_xlabel('Sunshine Hours per Day')
    ax1.set_ylabel('Density')
    ax1.grid(True, alpha=0.3)

    # Add some statistics lines
    mean_sunshine = daily['sunshine_hours'].mean()
    median_sunshine = daily['sunshine_hours'].median()
    ax1.axvline(x=mean_sunshine, color='red', linestyle='--', 
                label=f'Mean: {mean_sunshine:.2f} h')
    ax1.axvline(x=median_sunshine, color='blue', linestyle=':', 
                label=f'Median: {median_sunshine:.2f} h')
    ax1.legend()

    # Cumulative distribution on bottom
    ax2.plot(sorted_hours, cumulative, 'g-', linewidth=2)
    ax2.set_title('Cumulative Distribution of Sunshine Hours')
    ax2.set_xlabel('Sunshine Hours per Day')
    ax2.set_ylabel('Cumulative Probability')
    ax2.grid(True, alpha=0.3)

    # Add percentile markers
    percentiles = [25, 50, 75, 90, 95]
    for p in percentiles:
        percentile_value = np.percentile(daily['sunshine_hours'], p)
        ax2.axvline(x=percentile_value, color='gray', linestyle=':', alpha=0.5)
        ax2.text(percentile_value, 0.1, f'{p}%', rotation=90, 
                 verticalalignment='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(TMPPATH+'sunshine_distribution.png', dpi=150)
    print("   Saved: sunshine_distribution.png")
    uploadPNG(TMPPATH  + f'sunshine_distribution.png', DO_SCP, KEEP_PNG, SCP)
############################# new #################################################
    
    # 5. Cumulative sunshine by month
    print("5. Creating cumulative sunshine plot...")
    plt.figure(figsize=(12, 6))
    
    # Calculate cumulative sunshine by date
    daily_sorted = daily.sort_values('date').copy()
    daily_sorted['cumulative_sunshine'] = daily_sorted['sunshine_hours'].cumsum()
    
    plt.plot(daily_sorted['date'], daily_sorted['cumulative_sunshine'], 
             linewidth=2, color='orange')
    
    plt.title(f'Cumulative Sunshine Hours Over Time\n{MYPOSITION}')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Sunshine Hours')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(TMPPATH+'cumulative_sunshine.png', dpi=150)
    print("   Saved: cumulative_sunshine.png")
    uploadPNG(TMPPATH  + f'cumulative_sunshine.png', DO_SCP, KEEP_PNG, SCP)
    

    print(f"\nAll visualizations created successfully!")
    print(f"Location: {MYPOSITION}")

#---- from advanced_visualizations.py ---------------------------------------------------------------------------

#######################################################################################################

def year_type(value):
    current_year = datetime.now().year

    if value == "last":
        return current_year - 1

    try:
        year = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "year must be 'last' or a valid year number"
        )

    if year < 2014 or year > current_year:
        raise argparse.ArgumentTypeError(
            f"year must be between 2014 and {current_year}"
        )

    return year


#-------------------------------------------------------------------------------

SCRIPT_DESCRIPTION = 'WOSPi SUNSHINE ANALYSIS'
__VER__ = '1.0'
VERSION_STRING = '%%(prog)s: %s' % __VER__


def main():
    """Main function"""
    global solar_col_idx

    script = os.path.basename(__file__)
    example_usage  = 'e.g.:\n'
    example_usage += '\t' + script + ' -a y -y '+ str(yy) +'\t\t ... analyze yearly\n'
    example_usage += '\t' + script + ' -a y -y last\t\t ... analyze last year\n'
    example_usage += '\t' + script + ' -a m -y '+ str(yy) +' -m '+ str(mm) +'\t ... analyze monthly\n\n\n'

    argparser = argparse.ArgumentParser(
            usage='%(prog)s [options]',
            description=SCRIPT_DESCRIPTION,
            epilog=example_usage,
            formatter_class=argparse.RawTextHelpFormatter,
            prog=script)

    argparser.add_argument('-v', '--version',
            action='version', version=VERSION_STRING)

    argparser.add_argument('-a', '--analyze',
            required=True,
            choices = [ 'm', 'y', 'a' ],
            help='analyze data (y or m)')

    argparser.add_argument('-y', '--year',
            type=year_type,
            default=yy,
            help="year (2014..current year or 'last')")


    argparser.add_argument('-m', '--month',
            default=mm, type=int,
            help='set month for analyze=m')

    args = argparser.parse_args()


    if not args.analyze and not args.year:
        argparser.print_help()
        print()
        sys.exit(0)

    if args.analyze and not args.month:
        argparser.print_help()
        print()
        sys.exit(0)


    print("\n" + "="*70)
    print(SCRIPT_DESCRIPTION)
    print(f"Data directory: {CSVPATH}")
    print("="*70)

    # Parse position
    latitude, longitude = parse_position(MYPOSITION)
    print(f"Location: {latitude:.6f}°N, {longitude:.6f}°E")

    # Get available years
    available_years = get_available_years(CSVPATH)
    if args.year not in available_years:
        print(f"\nError: No data for year {args.year}.\nAvailable years in data: {available_years}")
        sys.exit()


    # Get solar column and threshold
    print("\n" + "="*50)
    print("SOLAR RADIATION SETTINGS")
    print("="*50)

    print(f"Using threshold: {solar_threshold} W/m²")

    year_input = args.year
    month_input = args.month

    if args.analyze == 'y':
        year = int(year_input)

        print(f"\nLoading data for {year}...")
        combined_df = load_and_combine_files(CSVPATH, year=year)

    elif args.analyze == 'a':
        # All years
        print(f"\nLoading all available data ({len(available_years)} years)...")
        combined_df = load_and_combine_files(CSVPATH)
        year = None

    elif args.analyze == 'm':
        # Specific month
        year = int(year_input)
        month = int(month_input)

        if month < 1 or month > 12:
            print("Month must be between 1 and 12!")
            return

        print(f"\nLoading data for {year}-{month:02d}...")
        combined_df = load_and_combine_files(CSVPATH, year=year, month=month)


    else:
        print("Invalid choice!")
        return

    if combined_df is None:
        print("Failed to load data!")
        return

    #-------------------------------------------------------------------------------

    # Analyze the solar radiation data
    result = analyze_solar_column(combined_df, solar_col_idx)
    if result is None:
        return

    df_with_solar, actual_solar_col_idx = result

    # Update solar column index if it was changed
    if actual_solar_col_idx != solar_col_idx:
        print(f"\nNote: Using column {actual_solar_col_idx} for solar radiation")
        solar_col_idx = actual_solar_col_idx


    # Calculate sunshine hours
    if args.analyze == 'y':
        # Specific year
        daily, monthly, hourly = calculate_sunshine(
            df_with_solar, latitude, longitude, solar_threshold, year
        )

        if daily is not None:
            # Create year-specific visualizations
            create_year_specific_visualizations(year)

            print("\n ### main_statistics ###" + "="*70)
            main_statistics(year)
            print("\n ### main_statistics ###" + "="*70)

    elif args.analyze == 'a':
        # All years
        daily, monthly, hourly = calculate_sunshine(
            df_with_solar, latitude, longitude, solar_threshold, None
        )

        # Create all-years visualizations
        #print("\nFor all-years visualizations, run:")
        #print("  python advanced_visualizations.py")

    elif args.analyze == 'm':
        # Specific month
        daily, monthly, hourly = calculate_sunshine(
            df_with_solar, latitude, longitude, solar_threshold, year
        )

    if daily is not None:
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)
        print("\nGenerated files:")

        if args.analyze == 'y':
            print(f"  daily_sunshine_{year}.csv")
            print(f"  monthly_sunshine_{year}.csv")
            print(f"  hourly_sunshine_profile_{year}.csv")
            #print(f"\nTo create charts for {year}:")
            #print(f"  gnuplot plot_daily_{year}.gp")
            #print(f"  gnuplot plot_monthly_{year}.gp")

            if not KEEP_TMP:
                daily_file = f'daily_sunshine_{year}.csv'
                monthly_file = f'monthly_sunshine_{year}.csv'
                hourly_file = f'hourly_sunshine_profile_{year}.csv'

                os.unlink(TMPPATH+daily_file)
                os.unlink(TMPPATH+monthly_file)
                os.unlink(TMPPATH+hourly_file)


        elif args.analyze == 'a':
            print("  daily_sunshine_all_years.csv")
            print("  monthly_sunshine_all_years.csv")
            print("  hourly_sunshine_profile_all_years.csv")
            #print("\nFor advanced visualizations:")
            create_all_visualizations()

            if not KEEP_TMP:
                daily_file = f'daily_sunshine_all_years.csv'
                monthly_file = f'monthly_sunshine_all_years.csv'
                hourly_file = f'hourly_sunshine_profile_all_years.csv'

                os.unlink(TMPPATH+daily_file)
                os.unlink(TMPPATH+monthly_file)
                os.unlink(TMPPATH+hourly_file)

        elif args.analyze == 'm':
            month_name = date(2000, month, 1).strftime('%B')
            print(f"  daily_sunshine_{year}.csv (for {month_name} {year})")
            print(f"  monthly_sunshine_{year}.csv")
            print(f"  hourly_sunshine_profile_{year}.csv")

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

