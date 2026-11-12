import sys
sys.path.insert(0,'/path/to/epm2-tools/tools')
import disasm
for fw in sys.argv[2:]:
    for b in (0,1):
        print(disasm.block_file(fw,b,cache_dir=sys.argv[1]))
