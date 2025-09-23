import argparse
import json
from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from vc.verifier import verify


def main() -> None:
	parser = argparse.ArgumentParser(description="Verify EIP-712 proofs for RWA VC")
	parser.add_argument("--in", dest="inp", required=True, help="Input issued VC JSON path")
	parser.add_argument("--keys", dest="keys", required=False, default="keys/keys.json", help="Keys config JSON path (optional)")
	args = parser.parse_args()

	inp = Path(args.inp)
	with inp.open("r", encoding="utf-8") as f:
		vc = json.load(f)

	expected = None
	keysp = Path(args.keys)
	if keysp.exists():
		with keysp.open("r", encoding="utf-8") as f:
			keys_cfg = json.load(f)
		expected = (keys_cfg or {}).get("addresses", None)

	results = verify(vc, expected_addresses=expected)

	ok_all = all(r.get("ok", False) for r in results)
	for r in results:
		print(r)
	print("OK:", ok_all)


if __name__ == "__main__":
	main()
