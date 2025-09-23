import argparse
import json
import os
from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from vc.issuer import issue
from vc.crypto import generate_private_key, private_key_to_address


def main() -> None:
	parser = argparse.ArgumentParser(description="Issue EIP-712 proofs for RWA VC")
	parser.add_argument("--in", dest="inp", required=True, help="Input VC JSON path")
	parser.add_argument("--out", dest="out", required=True, help="Output path for issued VC")
	parser.add_argument("--keys", dest="keys", required=False, default="keys/keys.json", help="Keys config JSON path")
	args = parser.parse_args()

	inp = Path(args.inp)
	outp = Path(args.out)
	keysp = Path(args.keys)

	with inp.open("r", encoding="utf-8") as f:
		vc = json.load(f)

	keys_cfg = {}
	if keysp.exists():
		with keysp.open("r", encoding="utf-8") as f:
			keys_cfg = json.load(f)
	else:
		keys_cfg = {"domain": {"name": "RWA-VC", "version": "1", "chainId": 1}, "keys": {}}

	issued, proofs = issue(vc, keys_cfg)

	outp.parent.mkdir(parents=True, exist_ok=True)
	with outp.open("w", encoding="utf-8") as f:
		json.dump(issued, f, ensure_ascii=False, indent=2)

	print("Issued VC written to:", str(outp))
	print("Proofs:")
	for p in proofs:
		print(p)


if __name__ == "__main__":
	main()
