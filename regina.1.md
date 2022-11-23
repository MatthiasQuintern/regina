% NICOLE(1) nicole 2.0
% Matthias Quintern
% April 2022

# Name
**R**uling **E**mpress **G**enerating **I**n-depth **N**ginx **A**nalytics (obviously)
Regina is an analytics tool for nginx.

## About
It collects information from the nginx access.log and stores it in a sqlite3 database.
Regina supports several data visualization configurations and can generate an admin-analytics page from an html template file.

# SYNOPSIS
| With config file:
|    **regina** [OPTION...]

## Visualization options:
- Line plot: Einmal seit Beginn der Aufzeichnung(pro Monat), einmal letzte 30 Tage (pro Tag)
  x: date 
  y: #unique users, #unique requests
- Bar charts:
  - unique user information:
    - used browsers (in percent)
    - used operating systems (in percent)
    - countries (in percent)
  - unique request information:
    - requested files (in counts)
    - HTTP referrers (in counts)
A unique user is a IP-address - user agent pair.
A unique request is a unique-user - requested file - date (day) - combination.

## Command line options
**-d** directory
: process directory [directory]

**-f** file
: process file [file]

**-r**
: go through directories recursively

**-s**
: silent, no command-line output

**-i**
: ignore history

**-n**
: do not write to history

**-o**
: overwrite if the file already has lyrics

**-t**
: test, do not write lyrics to file, but print to stdout

**-h**
: show this

**--rm_explicit**
: remove the "[Explicit]" lyrics warning from the song's title tag

**--site** site
: onlysearch [site] for lyrics (genius or azlyrics)

If you do not specify a directory or file, the program will ask you if you want to use the current working directory.
Example: `nicole -ior -d ~/music/artist --rm_explicit`

# INSTALLATION AND UPDATING
To update nicole, simply follow the installation instructions.

## pacman (Arch Linux)
Installing nicole using the Arch Build System also installs the man-page and a zsh completion script, if you have zsh installed.
```shell
git clone https://github.com/MatthiasQuintern/nicole.git
cd nicole
makepkg -si
```

## pip
You can also install nicole with python-pip:
```shell
git clone https://github.com/MatthiasQuintern/nicole.git
cd nicole
python3 -m pip install .
```
You can also install it system-wide using `sudo python3 -m pip install.`

If you also want to install the man-page and the zsh completion script:
```shell
sudo cp nicole.1.man /usr/share/man/man1/nicole.1
sudo gzip /usr/share/man/man1/nicole.1
sudo cp _nicole.compdef.zsh /usr/share/zsh/site-functions/_nicole
sudo chmod +x /usr/share/zsh/site-functions/_nicole
```

# CHANGELOG
## 1.0
- Initial release

# COPYRIGHT
Copyright  ©  2022  Matthias  Quintern.  License GPLv3+: GNU GPL version 3 <https://gnu.org/licenses/gpl.html>.\
This is free software: you are free to change and redistribute it.  There is NO WARRANTY, to the extent permitted by law.
