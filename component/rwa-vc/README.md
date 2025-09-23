## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Quick demo
python demo.py --in RWA-VC-example-vehicle.json --out out/demo.issued.json --keys keys/keys.json
# Options:
#   --in     Input VC JSON (default: RWA-VC-example-vehicle.json)
#   --out    Output issued VC (default: out/demo.issued.json)
#   --keys   Keys config (default: keys/keys.json)
```

## Development

```bash
# Issue specific VC
python -m scripts.issue --in RWA-VC-example-vehicle.json --out out/vehicle.issued.json --keys keys/keys.json
# Options:
#   --in     Input VC JSON (required)
#   --out    Output issued VC (required)
#   --keys   Keys config (default: keys/keys.json)

# Verify issued VC
python -m scripts.verify --in out/vehicle.issued.json --keys keys/keys.json
# Options:
#   --in     Issued VC JSON to verify (required)
#   --keys   Keys config (default: keys/keys.json) - enables strict address match

# Generate new keys
python -m scripts.gen_keys --out keys/keys.json
# Options:
#   --out    Output keys file (default: keys/keys.json)
```