% REGINA(1) regina 1.1
% Matthias Quintern
% May 2023

# NAME
regina - **R**uling **E**mpress **G**enerating **I**n-depth **N**ginx **A**nalytics (obviously)

## Description
`regina` is a **python**  <!-- ![python-logo](/resources/img/logos/python.svg "snek make analytics go brr") --> program that generates ***analytics*** for a static webpage serverd with **nginx**.
`regina` is easy to deploy and privacy respecting: 
  - it collects the data from the nginx logs: no javascript/changes to your website required
  - data is stored on your device in a **sqlite** database, nothing goes to any cloud
It parses the log and **stores** the important data in an *sqlite* <!-- ![sqlite-logo](/resources/img/logos/sqlite.svg) --> database. 
It can then create an analytics html page that has lots of useful **plots** and **numbers**.

<!-- ## Capabilities -->
<!-- ### Statistics -->
<!-- `regina` can generate the following statistics: -->

<!--   - visitor count history -->
<!--   - request count history -->
<!--   - referrer ranking *(from which site people visit)* -->
<!--   - route ranking *(accessed files)* -->
<!--   - browser ranking -->
<!--   - platform ranking *(operating systems)* -->
<!--   - city ranking *(where your site visitors are from)* -->
<!--   - country ranking -->
<!--   - mobile visitor percentage -->
<!--   - detect if a visitor is likely to be human or a bot -->

<!-- All of those plots and numbers can be generated for the **last x days** (you can set *x* yourself) and for **all times**. -->

<!-- ### Visualization -->
<!-- `regina` can use the data above to generate a static analytics page in a single html file. --> 
<!-- The visitor and ranking histories are included as plots. -->  
<!-- You can view an example page [here](https://quintern.xyz/en/software/regina-example.html) -->  
<!-- If that is not enough for you, you can write your own script and use data exported by regina or access the database directly. -->

# SYNOPSIS
| **regina** --config CONFIG_FILE [OPTION...]

# COMMAND LINE OPTIONS
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
- **sqlite >= 3.37**
- **python >= 3.10**
- **python-matplotlib**

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
    sudo cp regina/package-data/_regina.compdef.zsh /usr/local/share/zsh/site-functions/_regina
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
`10 0 * * * /usr/bin/regina --config /home/myuser/.config/regina/regina.cfg --collect --visualize`
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

To configure regina to use the GeoIP database, edit `get_visitor_location` and `get_cities_for_contries` in section `data-collection`.  
By default, `regina` only tells you which country a user is from. 
Append the two-letter country codes for countries you are interested in to the `get_cities_for_contries` option.  
After that, add the GeoIP-data into your database:
```
    regina --config regina.cfg --update-geoip path-to-csv
```
Depending on how many countries you specified, this might take a long time. You can delete the `csv` afterwards.


# CUSTOMIZATION
## Generated html
The generated file does not need to be an html. The template can be any text file.  
`regina` will only replace certain words starting with a `%`.
You can see all supported variables and their values by running `--visualize` with `debug_level = 1`.

## Data export
If you want to further process the data generated by regina, you can export the data by setting the `data_out_dir` in the `data-export` section.
The data can be exported as `csv` or `pkl`.  
If you choose `pkl` as filetype, all rankings will be exported as python type `list[tuple[int, str]]`.

## Database
You can of course work directly with the database, as long as it is not altered.
Editing, adding or deleting entries might make the database incompatible with regina, so only do that if you know what you are doing.
Just querying entries will be fine though.

# TROUBLESHOOTING
## General
If you are having problems, try setting the `debug_level` in section `debug` of the configuration file to a non-zero value.

## sqlite3.OperationalError: near "STRICT": syntax error
Your sqlite3 version is probably too old. Check with `sqlite3 --version`. `regina` requires 3.37 or higher.  
Hotfix: Remove all `STRICT`s from `<python-dir>/site-packages/regina/sql/create_db.sql`.

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
