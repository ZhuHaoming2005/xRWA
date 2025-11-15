# xRWA - Cross-Chain Real World Assets

## CrossChainChannel Component

An implementation of cross-chain asset swaps enabling atomic, batched exchanges between different asset types.

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

## SPV-based Authentication and RWA VC Component

A demo implementation showcasing the flow of RWA Verifiable Credentials with EIP-712 signatures and SPV-based cross-chain authentication. This is a demonstration codebase, not intended for production use.

### Quick Start

```bash
cd component

# Install dependencies
pip install -r requirements.txt
npm install

# Start a dual-chain environment (needs 2 terminals)
npm run chain1  # Terminal 1
npm run chain2  # Terminal 2

# Deploy contracts
npx truffle migrate --network chain1
npx truffle migrate --network chain2

# Demonstrate the issuance and verification process.
python demo.py --in vc-schema/RWA-VC-example-vehicle.json --out out/demo.issued.json --keys keys/keys.json
# Options:
#   --in     Input VC JSON (default: vc-schema/RWA-VC-example-vehicle.json)
#   --out    Output issued VC (default: out/demo.issued.json)
#   --keys   Keys config (default: keys/keys.json)

# Run cross-chain authentication. You must run demo.py first to issue a VC.
node scripts/cross_chain_demo.js
```

### Development

```bash
# Generate signing keys
python -m scripts.gen_keys --out keys/keys.json
# Options:
#   --out    Output keys file (default: keys/keys.json)

# Issue specific VC
python -m scripts.issue --in vc-schema/RWA-VC-example-vehicle.json --out out/vehicle.issued.json --keys keys/keys.json
# Options:
#   --in     Input VC JSON (required)
#   --out    Output issued VC (required)
#   --keys   Keys config (default: keys/keys.json)

# Verify issued VC
python -m scripts.verify --in out/vehicle.issued.json --keys keys/keys.json
# Options:
#   --in     Issued VC JSON to verify (required)
#   --keys   Keys config (default: keys/keys.json) - enables strict address matching

# Truffle commands
npx truffle compile
npx truffle migrate --network chain1
npx truffle migrate --network chain2
```

### Demo Flow Overview

1. Issue VC with EIP-712 proofs using Python scripts
2. Register VC commitment on Chain 1 (VCRegistry)
   - Uses mock tokenization tx for demo
   - Computes commitment from VC fields
3. Generate SPV proof from Chain 1 block
   - Builds Merkle tree from block transactions
4. Submit proof to Chain 2 (SPVVerifier)
   - Simulates light client header sync
5. Verify proof and embedded commitment

### Important Notes

- This is a demonstration codebase to illustrate the cross-chain VC verification flow.
- Several components are simplified for clarity:
  - Uses mock transactions instead of actual RWA tokenization
  - Simplified light client header synchronization
  - Basic key management
  - No access control or rate limiting
- For production implementations, additional considerations are needed:
  - Secure key management
  - Proper light client implementation
  - Oracle integration for header sync
  - Gas optimization
  - Access control
  - Proper error handling

## License

MIT License - see [LICENSE](LICENSE) for details.

It also provided technical support for Cross-Channel [TC'23].