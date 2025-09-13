# xRWA - Cross-Chain Real World Assets

## CrossChainChannel Component

Cross-chain asset swap implementation for atomic exchanges between different asset types.

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

## SPV and VC Component

Check the SPV and VC performance test in scripts folder.

## License

MIT License - see [LICENSE](LICENSE) for details.
