import argparse
import json
from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from vc.issuer import issue
from vc.verifier import verify


def main() -> None:
	parser = argparse.ArgumentParser(description="RWA-VC demo: issue and verify in one run")
	parser.add_argument("--in", dest="inp", default="RWA-VC-example-vehicle.json", help="Input VC JSON path")
	parser.add_argument("--out", dest="out", default="out/demo.issued.json", help="Output path for issued VC")
	parser.add_argument("--keys", dest="keys", default="keys/keys.json", help="Keys config JSON path")
	args = parser.parse_args()

	inp = Path(args.inp)
	outp = Path(args.out)
	keysp = Path(args.keys)

	print("RWA-VC Demo - Issue & Verify")
	print("--------------------------------------------------")
	print("1) Loading input VC:", str(inp))
	with inp.open("r", encoding="utf-8") as f:
		vc = json.load(f)

	print("2) Loading keys config:", str(keysp))
	if keysp.exists():
		with keysp.open("r", encoding="utf-8") as f:
			keys_cfg = json.load(f)
	else:
		keys_cfg = {
			"domain": {"name": "RWA-VC", "version": "1", "chainId": 1},
			"keys": {"identity": "auto", "compliance": "auto", "custody": "auto", "document": "auto"},
		}
		print("   (keys.json not found; using auto-generated keys)")

	print("3) Issuing EIP-712 proofs...")
	issued, proofs = issue(vc, keys_cfg)
	for p in proofs:
		print("   *", p)

	outp.parent.mkdir(parents=True, exist_ok=True)
	with outp.open("w", encoding="utf-8") as f:
		json.dump(issued, f, ensure_ascii=False, indent=2)
	print("   -> Issued VC saved to:", str(outp))

	print("4) Verifying proofs...")
	expected = (keys_cfg or {}).get("addresses")
	results = verify(issued, expected_addresses=expected)
	ok_all = all(r.get("ok", False) for r in results)
	for r in results:
		print("   *", r)
	print("Final result:", "VALID" if ok_all else "INVALID")


if __name__ == "__main__":
	main()
