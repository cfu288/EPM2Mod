#!/bin/zsh
# crawls.sh: shallow menu crawls of the pinned image and the debug-log image, four configurations, then the compare
cd ${0:A:h}/.. && . ./env.sh
for c in p-nocard-shallow iauto-nocard-shallow art-card-shallow movie-card-shallow; do
  log/crawl-all.sh $c log-pinned log-debug > log/crawl-$c.out 2>&1
  python3 log/crawlcmp.py log/crawl/$c/log-pinned log/crawl/$c/log-debug log/diff/$c
done > log/crawl-shallow.txt 2>&1
echo crawls done
