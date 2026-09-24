"""Build a delivery ZIP from explicit local rule files (no network access)."""
import argparse
from pathlib import Path
from contest_rules import loads
from rule_pack import build

def main():
    p=argparse.ArgumentParser(description='PSLogルール配布パックを作成')
    p.add_argument('output',type=Path);p.add_argument('rules',type=Path,nargs='+')
    p.add_argument('--pack-id',required=True);p.add_argument('--revision',required=True,type=int)
    p.add_argument('--minimum-version',default='1.01')
    a=p.parse_args()
    build(a.output,[(loads(f.read_text(encoding='utf-8-sig')),a.revision,a.minimum_version) for f in a.rules],a.pack_id)
    print(a.output.resolve())
if __name__=='__main__':main()
