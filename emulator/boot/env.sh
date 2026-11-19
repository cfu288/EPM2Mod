# env.sh: sourced by the zsh scripts of this folder. Every path comes from the environment or from the repository.
#   EPM2_REPO     the repository root (default: three folders above this file)
#   OM_EMU_NODE   Node 26 or newer (default: found by emulator/emuenv.py)
#   EMU_OUT       where the scripts write their output folders (default: build/emu/out, ignored by git)
#   EMU_STATE     where the settings states are (default: build/emu/state; made by emulator/mkstate)
EPM2_REPO=${EPM2_REPO:-${${(%):-%x}:A:h:h:h}}
export EPM2_REPO
EMU=$EPM2_REPO/emulator
BOOT=$EMU/boot
NODE=${OM_EMU_NODE:-$(python3 -c "import sys; sys.path.insert(0, '$EMU'); import emuenv; print(emuenv.node())")} || { echo "no Node 26: set OM_EMU_NODE" >&2; exit 3 }
export OM_EMU_DIR=${OM_EMU_DIR:-$(python3 -c "import sys; sys.path.insert(0, '$EMU'); import emuenv; print(emuenv.require_om_emu())")} || { echo "run emulator/setup.sh first" >&2; exit 3 }
EMU_OUT=${EMU_OUT:-$EPM2_REPO/build/emu/out}
EMU_STATE=${EMU_STATE:-$EPM2_REPO/build/emu/state}
# blocks IMAGE -> the folder of unpacked blocks (stock, data/builds/NAME.json, a .BIN file or a folder)
blocks() { $EMU/emu-run --blocks $1 || { echo "cannot unpack $1" >&2; exit 3 } }
# imgname IMAGE -> the short name used for output folders and state files (stock, peaking-colours, ...)
imgname() { local n=${1:t}; print -r -- ${n%.*} }
# state IMAGE MODE -> the state file EMU_STATE/NAME-MODE.json; made with emulator/mkstate when it is missing
state() {
  local f=$EMU_STATE/$(imgname $1)-$2.json
  [[ -f $f ]] || $EMU/mkstate $1 $f $2 >&2 || { echo "cannot make the state $f" >&2; exit 3 }
  print -r -- $f
}
