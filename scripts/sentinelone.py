#!/usr/bin/python

import subprocess
import json
import sys
import os
import plistlib
import dateutil.parser as dp
from distutils.version import LooseVersion
import time


def dict_clean(items):
    result = {}
    for key, value in items:
        if value is None:
            value = 'None'
        result[key] = value
    return result

def main():
    s1_binary = '/Library/Sentinel/sentinel-agent.bundle/Contents/MacOS/sentinelctl'

    # Skip manual check
    if len(sys.argv) > 1:
        if sys.argv[1] == 'manualcheck':
            print 'Manual check: skipping'
            exit(0)

    # Create cache dir if it does not exist
    cachedir = '%s/cache' % os.path.dirname(os.path.realpath(__file__))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)


    if os.path.isfile(s1_binary):
        version_command = [s1_binary, 'version']
        version_task = subprocess.Popen(version_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        (version, stderr) = version_task.communicate()
        version = version.split(" ")[1]
        
        if LooseVersion(version) < LooseVersion("3.2.0"):
            summary_command = [s1_binary, 'summary', 'json']
            task = subprocess.Popen(summary_command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            (stdout, stderr) = task.communicate()
            # Sentinel One's output has a header of "Summary information" that needs to be stripped off to be proper json
            s1_summary = json.loads(stdout.split('\n',1)[1], object_pairs_hook=dict_clean)
            # convert the ISO time to epoch time and store back in the variable
            s1_summary['last-seen'] = dp.parse(s1_summary['last-seen']).strftime('%s')
        else:
            
            summary_command = [s1_binary, 'status', '--filters', 'Agent,Management']
            task = subprocess.Popen(summary_command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            (stdout, stderr) = task.communicate()
            stdout = stdout.split('\n')
            s1_summary = {}
            for line in stdout:
                #Strip all the whitespace in the formatted output
                line = "".join(line.split())
                #Break the line up into parts to make sure there are key and values
                parts = line.split(':', 1)
                # If the number of parts is less than 2 there's not a key/value pair
                if len(parts) > 1:
                    #Split the line of text into a dict for parsing
                    line = dict([line.split(':', 1)])
                    mydict = dict(line)
                    for title, description in mydict.items():
                        # For keys with dates, convert date format into epoch for processing on MR
                        if title in 'LastSeen' or title in 'InstallDate':
                            pattern = '%m/%d/%y,%I:%M:%S%p'
                            try:
                                s1_summary[title] = int(time.mktime(time.strptime(description.strip(), pattern)))
                            except ValueError:
                                s1_summary[title] = 0
                        else:
                            s1_summary[title] = description.strip()
    
        # Write to disk
        output_plist = os.path.join(cachedir, 'sentinelone.plist')
        plistlib.writePlist(s1_summary, output_plist)
    else:
        print "SentinelOne's sentinelctl binary missing. Exiting."
        exit(0)

if __name__ == "__main__":
    main()
