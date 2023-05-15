% REGINA(1) regina 1.1
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

# GETTING STARTED

## Dependencies
- **nginx**: You need a nginx webserver that outputs the access log in the `combined` format, which is the default
- **Python 3.10**
- **Python/matplotlib**

## Installation
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
    sudo cp regina/package-data/_regina.compdef.zsh /usr/share/zsh/site-functions/_regina
    sudo chmod +x /usr/share/zsh/site-functions/_regina
```

## Configuration
The following instructions assume you have an nginx webserver configured for a website like this, with `/www` as root (`/`):
```
    /www
    |-- resources
    |   |-- image.jpg
    |-- index.html
```
By default, nginx will generate logs in the `combined` format with the name `access.log` in `/var/log/nginx/` and rotate them daily.

Copy the default configuration and template from the git directory to a directory of your choice, in this case `~/.config/regina`
If you did clone the git repo, the files should be in `/usr/local/lib/python3.11/site-packages/regina/package-data/`.
```shell
    mkdir ~/.config/regina
    cp regina/package-data/default.cfg ~/.config/regina/regina.cfg
    cp regina/package-data/template.html ~/.config/regina/template.html
```
Now edit the configuration to fit your needs.
For our example:
```
    [regina]
    server_name = my_server.com
    access_log = /var/log/nginx/access.log.1
    ...
    [html-generation]
    html_out_path = /www/analytics/analytics.html
    img_location = /img

    [plot-generation]
    img_out_dir = /www/analytics/img
```
Most defaults should be fine.  The default configuration should also be documented well enough for you to know what do do. 
It is strongly recommended to only use absolute paths.

Now you fill collect the data from the nginx log specified as `access_log` in the configuration into the database specified at the `database` location (or `~/.local/share/regina/my-server.com.db` if left blank):
```
    regina --config ~/.config/regina/regina.cfg --collect
```

To visualize the data, run:
```
    regina --config ~/.config/regina/regina.cfg --visualize
```
This will generate plots and statistics and replace all variables in `template_html` and output the result to `html_out_path`. 
If `html_out_path` is in your webroot, you should now be able to access the generated site.  
In our example, `/www` will look like this:
```
    /www
    |-- analytics
    |   |-- analytics.html
    |   |-- img
    |       |-- ranking_referer_total.svg
    |       |-- ranking_referer_last_x_days.svg
    |       ...
    |-- resources
    |   |-- image.jpg
    |-- index.html
    
```

### Automation
You will probably run `regina` once per day, after `nginx` has filled the daily access log. The easiest way to that is using a *cronjob*.
Run `crontab -e` and enter:
`10 0 * * * /usr/bin/regina --config /home/myuser/.config/regina/regina.conf --collect --visualize`
This assumes, you installed `regina` system-wide.  
Now the `regina` command will be run every day, ten minutes after midnight.
After each day, rotates the logs, so  `access.log` becomes `access.log.1`.
Since `regina` is run after the log rotation, you will probably want to run it on `access.log.1`.

#### Logfile permissions
By default, `nginx` logs are `-rw-r----- root root` so you can not access them as user.
You could either run regina as root, which I **strongly do not recommend** or make a root-cronjob that changes ownership of the log after midnight.
Run `sudo crontab -e` and enter:
`9 0 * * * chown your-username  /var/log/nginx/access.log.1`
This will make you the owner of the log 9 minutes after midnight, just before `regina` needs read access.


## GeoIP
`regina` can show you from which country or city a visitor is from, but you will need an *ip2location* database. 
You can acquire such a database for free at [ip2location.com](https://lite.ip2location.com/) (and probably some other sites as well!).
After creating create an account you can download several different databases in different formats.  
For `regina`, download the `IP-COUNTRY-REGION-CITY` for IPv4 as *csv*. 
By default, `regina` only tells you which country a user is from.
To see the individual cities for countries, append the two-letter country code to the `get_cities_for_contries` option in the `data-collection` section in the config file.
After that, oad the GeoIP-data into your database:
```
    regina --config regina.conf --update-geoip path-to-csv
```
Depending on how many countries you specified, this might take a long time. You can delete the `csv` afterwards.

# CHANGELOG
## 1.1
- Improved database format: 
    - put referrer, browser and platform in own table to reduze size of the database
    - route groups now part of visualization, not data collection
- Data visualization now uses more sql for improved performance
- Refactored codebase
- Bug fixes
- Changed setup.py to pyproject.toml
## 1.0
- Initial release

# COPYRIGHT
Copyright  ©  2022  Matthias  Quintern.  License GPLv3+: GNU GPL version 3 <https://gnu.org/licenses/gpl.html>.\
This is free software: you are free to change and redistribute it.  There is NO WARRANTY, to the extent permitted by law.
