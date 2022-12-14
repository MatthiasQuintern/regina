% NICOLE(1) nicole 2.0
% Matthias Quintern
% April 2022

# NAME
regina - **R**uling **E**mpress **G**enerating **I**n-depth **N**ginx **A**nalytics (obviously)

# SYNOPSIS
| **regina** --config CONFIG_FILE [OPTION...]

# DESCRIPTION
Regina is an analytics tool for nginx.
It collects information from the nginx access.log and stores it in a sqlite3 database.
Regina supports several data visualization configurations and can generate an admin-analytics page from an html template file.

## Command line options
**-h**, **--help**
: Show the the possible command line arguments

**-c**, **--config** config-file
: Retrieve settings from the config-file

**--access-log** log-file
: Overrides the access_log from the configuration

**--collect**
: Collect information from the access_log and store them in the databse

**--visualize**
: Visualize the data from the database

**--update-geoip** geoip-db
: Recreate the geoip part of the database from the geoip-db csv. The csv must have this form: lower, upper, country-code, country-name, region, city

# INSTALLATION AND UPDATING
## pip
You can install regina with python-pip:
```shell
git clone https://github.com/MatthiasQuintern/regina.git
cd regina
python3 -m pip install .
```
You can also install it system-wide using `sudo python3 -m pip install .`

If you also want to install the man-page and the zsh completion script:
```shell
sudo cp regina.1.man /usr/share/man/man1/regina.1
sudo gzip /usr/share/man/man1/regina.1
sudo cp _regina.compdef.zsh /usr/share/zsh/site-functions/_regina
sudo chmod +x /usr/share/zsh/site-functions/_regina
```

# CHANGELOG
## 1.0
- Initial release

# COPYRIGHT
Copyright  ©  2022  Matthias  Quintern.  License GPLv3+: GNU GPL version 3 <https://gnu.org/licenses/gpl.html>.\
This is free software: you are free to change and redistribute it.  There is NO WARRANTY, to the extent permitted by law.
