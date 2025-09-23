# xRWA - Cross-Chain Real World Assets

## CrossChainChannel Component

Cross-chain asset swap implementation for atomic multi-batch exchanges between different asset types.

### Features

- **ETH ↔ ERC20** atomic swaps
- **ETH ↔ ERC721** atomic swaps  
- **ERC20 ↔ ERC721** atomic swaps
- Timeout-based refund mechanism
- Multi-signature channel state updates

### Quick Start

```bash
# Install dependencies
npm install

# Run tests
npx truffle test
```

### Development

```bash
# Run specific test
npx truffle test test/ETHtoERC20Swap.test.js

# Compile contracts
npx truffle compile

# Deploy to networks
npx truffle migrate --network net1
npx truffle migrate --network net2
```

## RWA Verifiable Credentials Component

The RWA VC demo is located in the component/rwa-vc folder. For convenience, the demo uses fixed key pairs, but you can regenerate keys with the command below.

### Quick Start

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

### Development

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

## SPV and VC Component

Check the SPV and VC performance test in scripts folder.

## License

MIT License - see [LICENSE](LICENSE) for details.
