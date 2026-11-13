import sys
sys.path.insert(0,'/path/to/EPM2Mod/tools')
import disasm
for fw in sys.argv[2:]:
    for b in (0,1):
        print(disasm.block_file(fw,b,cache_dir=sys.argv[1]))
