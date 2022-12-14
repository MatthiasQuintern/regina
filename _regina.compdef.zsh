#compdef regina
# https://zsh.sourceforge.io/Doc/Release/Completion-System.html#Completion-Functions
_config-file() {
    # list all files that end in .conf
    # -s separator, descritions options
    _values -s , 'config files' $(find . -type f -name '*.conf')
}
_csv-file() {
    _values -s , 'geoip city database as csv' $(find . -type f -name '*.csv')
}

_regina() {
    # each argument is
    # n:message:action
    # option[description]:message:action
    # # -s allow stacking, eg -inr
    _arguments -s \
        {--help,-h}'[show help]' \
        {--config,-c}'[use this config file]':config:_config-file \
        '--visualize[visualize the data in the database]' \
        '--collect[collect requests from the nginx log]' \
        '--access-log[source this logfile]':logfile:_file \
        '--update-geoip[recreate the geoip database from csv]':csv:_csv-file
}
_regina "$@"
