# mirthpy-scripts
Useful scripts to run with mirthpy

## Advanced Mirth Search
This script will look in the designated mirth instances for channels that have the value you want to search for, in the property you want to search in.
It will display the matches with the Channel Name, Source or Destination Connector, Property Value, Line # (if applicable)

This script takes the following parameters:
- Instances - what mirth instances you want to search in
- Property - what property you want to search in (port, javascript, usernames, etc.)
- Value - what value you want to search for 
- Enabled Flag - if you want to just look at enabled channels, destinations, etc.
- Exact Match - if you want to look at matches that are only the exact match to the value
- Username - username for mirth
- Password - password for mirth