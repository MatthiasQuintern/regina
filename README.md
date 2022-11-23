# Regina
Regina is an analytics tool for nginx.
**R**uling **E**mpress **G**enerating **I**n-depth **N**ginx **A**nalytics (obviously)

## About
It collects information from the nginx access.log and stores it in a sqlite3 database.
Regina supports several data visualization configurations and can generate an admin-analytics page from an html template file.

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
