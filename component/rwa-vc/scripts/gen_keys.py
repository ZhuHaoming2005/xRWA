import argparse
import json
from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from vc.crypto import generate_private_key, private_key_to_address


def main() -> None:
	parser = argparse.ArgumentParser(description="Generate keys.json for RWA-VC demo")
	parser.add_argument("--out", dest="out", default="keys/keys.json", help="Output keys.json path")
	args = parser.parse_args()

	outp = Path(args.out)

	cfg = {
		"domain": {"name": "RWA-VC", "version": "1", "chainId": 1},
		"keys": {},
	}

	for name in ["identity", "compliance", "custody", "document"]:
		priv = generate_private_key()
		cfg["keys"][name] = priv

	cfg["addresses"] = {k: private_key_to_address(v) for k, v in cfg["keys"].items()}

	outp.parent.mkdir(parents=True, exist_ok=True)
	with outp.open("w", encoding="utf-8") as f:
		json.dump(cfg, f, ensure_ascii=False, indent=2)
	print("Wrote:", str(outp))
	for role, addr in cfg["addresses"].items():
		print(f"{role}: {addr}")


if __name__ == "__main__":
	main()

