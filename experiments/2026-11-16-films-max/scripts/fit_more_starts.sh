#!/bin/sh
# Second pass of fit_more.sh: the same model-only fits started from the three installed looks (not Portra, not the
# film itself) whose targets are nearest (results/distances.tsv). Output: out/fit_film-NAME-n2.npz.
#   sh experiments/2026-11-16-films-max/scripts/fit_more_starts.sh [JOBS]
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/../../2026-11-09-film-portra"
jobs=${1:-7}
L=out/lut/spektrafilm_v034
cat <<LIST | OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 xargs -P "$jobs" -L 1 sh -c '../../.venv/bin/python -I ../2026-11-16-films-max/scripts/fit_starts.py --starts $4 --lut '"$L"'_$2_1lut_vlog_srgb/lut_v034_$3.cube --name film-$1-n2 --edge-weight 0.25 > out/more2_$1.log 2>&1 || echo "FAILED $1"' fit
portra800 portra800_portraendura portra800_portraendura superia400,pro400h,velvia100
c200 c200_crystalarchive c200_crystalarchive superia400,pro400h,vision3250d
ctrl-velvia100 fujifilm_velvia_100_scanfilm velvia100_portraendura ektachrome,pro400h,kodachrome64
portra4002383 portra400_2383 portra400_2383 vision3250d,pro400h,superia400
gold200ca gold200_crystalarchive gold200_crystalarchive pro400h,vision3250d,superia400
provia100f fujifilm_provia_100f_scanfilm provia100f_portraendura ektachrome,velvia100,kodachrome64
ektar100 ektar100_portraendura ektar100_portraendura pro400h,vision3250d,velvia100
vision3500t vision3500t_2383 vision3500t_2383 vision3250d,pro400h,ektachrome
vision350d vision350d_2383 vision350d_2383 vision3250d,pro400h,ektachrome
vision3200t vision3200t_2383 vision3200t_2383 vision3250d,pro400h,ektachrome
verita200d verita200d_2383 verita200d_2383 vision3250d,pro400h,ektachrome
gold200 gold200_portraendura gold200_portraendura pro400h,ektachrome,velvia100
portra160 portra160_portraendura portra160_portraendura pro400h,ektachrome,vision3250d
ultramax400 ultramax400_portraendura ultramax400_portraendura pro400h,ektachrome,vision3250d
ctrl-portra portra400_portraendura portra400_portraendura pro400h,ektachrome,vision3250d
LIST
grep -h "this fit, predicted" out/film-*-n2_report.txt | wc -l
