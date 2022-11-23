#compdef nicole
# https://zsh.sourceforge.io/Doc/Release/Completion-System.html#Completion-Functions
_lyrics-site()
{
    _values "lyrics site" \
        'genius[use only genius.com]' \
        'azlyrics[use only azlyrics.com]' \
        'all[use all supported sites (default)]'
}

_nicole()
{
    # each argument is
    # n:message:action
    # option[description]:message:action
    # # -s allow stacking, eg -inr
    _arguments -s \
        '-d[process directory]':directory:_directories \
        '-f[process file]':file:_files \
        '-r[go through directories recursively]' \
        '-s[silent]' \
        '-i[ignore history]' \
        '-n[do not write to history]' \
        '-o[overwrite if the file already has lyrics]' \
        '-t[test, only print lyrics, dont write to tags]' \
        '-h[show this]' \
        '--rm_explicit[remove the "Explicit" lyrics warning from the title tag]' \
        '--site[specify lyrics site]':lyrics-site:_lyrics-site
}
_nicole "$@"
