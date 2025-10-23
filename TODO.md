
# Delete unnecessary functions
1. Not sure if we need rooftops.sampling or visualization.py. If not, delete them.
2. Go through example notebooks in pin_drop_sampling2 and update the matching functions. 
3. Go through pyproject.toml and check if I should drop any dependencies

# Add functionality
1. Might be useful to have a function that spits out the kmls in exactly the format required

# Add unit tests
Not sure if this is really necessary or if I should do it at all. 

# Other 
1. Confirm that this works as a package by creating a new, small repo, installing this from github, and then checking that everything works