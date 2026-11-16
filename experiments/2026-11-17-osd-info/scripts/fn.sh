#!/bin/sh
# fn.sh ADDR [MAXLINES]: print one function of the function listing build/map/functions.txt
# (made by tools/fwmap.py). ADDR is 8 hex digits, lower case. Run from the repository root.
M=build/map/functions.txt
n=$(grep -n -m1 "^$1 <f_$1>:" $M | cut -d: -f1)
[ -z "$n" ] && { echo "no function $1"; exit 1; }
tail -n +$n $M | awk -v max=${2:-400} 'NR>1 && /^[0-9a-f]+ <f_/ {exit} NR<=max {print}' | sed 's/<f_[0-9a-f]*>//; s/^\(7e[0-9a-f]*\):\t/\1 /'
