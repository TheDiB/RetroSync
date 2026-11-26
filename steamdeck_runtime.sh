#!/bin/sh
# Experimental cooperative launcher. Use only a trusted private local fixture.
# Never create, truncate, replace or unlink the lock file here.
set -eu

blocked() {
    printf 'RetroSync runtime blocked: %s\n' "$*" >&2
    exit 125
}

[ "$#" -eq 0 ] || blocked "Unexpected arguments"
case "$0" in
    /*/steamdeck_runtime.sh) root=${0%/*} ;;
    *) blocked "Expected absolute launcher path" ;;
esac

[ "$(realpath -e -- "$root")" = "$root" ] ||
    blocked "Noncanonical fixture directory"
uid=$(id -u) || blocked "Cannot identify user"
[ -d "$root" ] && [ ! -L "$root" ] ||
    blocked "Invalid fixture directory"
[ "$(stat -c '%u:%a' -- "$root")" = "$uid:700" ] ||
    blocked "Expected private owned fixture directory"

case "$(pwd -P)" in
    */steamapps/common/RetroArch) ;;
    *) blocked "Unexpected working directory" ;;
esac
[ -f ./retroarch ] && [ -x ./retroarch ] ||
    blocked "RetroArch unavailable"
[ -x /usr/bin/flock ] || blocked "flock unavailable"

lock="$root/retrosync.lock"
[ -f "$lock" ] && [ ! -L "$lock" ] ||
    blocked "Invalid lock file"
[ "$(stat -c '%u:%a:%h' -- "$lock")" = "$uid:600:1" ] ||
    blocked "Unsafe lock metadata"
identity=$(stat -c '%d:%i' -- "$lock") ||
    blocked "Cannot identify lock"

# Read-only open: Linux flock supports exclusive locks on local files
# opened read-only. The trusted directory must not be mutated concurrently.
# A failed exec redirection can terminate a POSIX shell; isolate the open
# and launch in a subshell, with the outer shell replaced by no writer.
(
    exec 3< "$lock" || exit 125
    fd="/proc/self/fd/3"
    [ -f "$fd" ] || blocked "Invalid lock descriptor"
    [ "$(stat -L -c '%u:%a:%h' -- "$fd")" = "$uid:600:1" ] ||
        blocked "Unsafe descriptor metadata"
    [ "$(stat -L -c '%d:%i' -- "$fd")" = "$identity" ] ||
        blocked "Lock identity changed"
    if /usr/bin/flock -n -E 75 3; then
        :
    else
        rc=$?
        [ "$rc" -eq 75 ] && exit 75
        blocked "Cannot acquire lock"
    fi
    [ ! -L "$lock" ] &&
        [ "$(stat -c '%d:%i' -- "$lock")" = "$identity" ] ||
        blocked "Lock path changed after acquisition"
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}:$(pwd)"
    exec ./retroarch
) 
