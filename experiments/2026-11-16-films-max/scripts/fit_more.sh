#!/bin/sh
# Model-only fits (no --anchor) of more film stocks, with the method of the seven installed looks
# (fit_film2.py, model2, --edge-weight 0.25; NOTES §45.3 of 2026-11-09-film-portra).
# Also two controls: Portra 400 and Velvia 100 fitted the same way, without their camera anchor.
#   sh experiments/2026-11-16-films-max/scripts/fit_more.sh [JOBS]
# Output: experiments/2026-11-09-film-portra/out/fit_film-NAME-n1.npz, out/film-NAME-n1_report.txt, out/more_NAME.log
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/../../2026-11-09-film-portra"
jobs=${1:-7}
L=out/lut/spektrafilm_v034
# short name, LUT folder stem, cube file stem
cat <<LIST | OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 xargs -P "$jobs" -L 1 sh -c '../../.venv/bin/python -I fit_film2.py --lut '"$L"'_$2_1lut_vlog_srgb/lut_v034_$3.cube --name film-$1-n1 --edge-weight 0.25 > out/more_$1.log 2>&1 || echo "FAILED $1"' fit
ektar100 ektar100_portraendura ektar100_portraendura
provia100f fujifilm_provia_100f_scanfilm provia100f_portraendura
gold200 gold200_portraendura gold200_portraendura
gold200ca gold200_crystalarchive gold200_crystalarchive
portra160 portra160_portraendura portra160_portraendura
vision3500t vision3500t_2383 vision3500t_2383
portra800 portra800_portraendura portra800_portraendura
c200 c200_crystalarchive c200_crystalarchive
ultramax400 ultramax400_portraendura ultramax400_portraendura
vision350d vision350d_2383 vision350d_2383
vision3200t vision3200t_2383 vision3200t_2383
verita200d verita200d_2383 verita200d_2383
portra4002383 portra400_2383 portra400_2383
ctrl-portra portra400_portraendura portra400_portraendura
ctrl-velvia100 fujifilm_velvia_100_scanfilm velvia100_portraendura
LIST
grep -h "this fit, predicted" out/film-*-n1_report.txt | wc -l
