
# Delete unnecessary functions
1. Not sure if we need rooftops.sampling or visualization.py. If not, delete them.
2. Go through example notebooks in pin_drop_sampling2 and update the matching functions. 
3. Go through pyproject.toml and check if I should drop any dependencies

# Add functionality
1. Create function that generates google map directions or google map location (see pin_drop_sampling2/demo_philippines). This could be an easy row-wise function that I use with apply(axis=1) or that takes two series and returns a series
2. Create function that saves kmls in the format necessary to create a map.

# Add demo notebook
1. The notebook should start from a list of downloaded PSUs (barangays, )

# Update the README
The README should include information about how to install the package and how to use it to select a sample.

# Add unit tests
Not sure if this is really necessary or if I should do it at all. 

# Other 
1. Confirm that this works as a package by creating a new, small repo, installing this from github, and then checking that everything works