const Web3 = require('web3');
const fs = require('fs');
const { MerkleTree } = require('merkletreejs');
const VCRegistry = require('../build/contracts/VCRegistry.json');
const SPVVerifier = require('../build/contracts/SPVVerifier.json');

// Connect to both chains
const web3_c1 = new Web3('http://localhost:8545');
const web3_c2 = new Web3('http://localhost:8546');

async function demo() {
    try {
        console.log('Loading contracts and accounts...');
        
        // Load issued VC
        const issuedVC = JSON.parse(fs.readFileSync('./out/demo.issued.json', 'utf8'));
        
        // Setup contracts and accounts
        const accounts_c1 = await web3_c1.eth.getAccounts();
        const accounts_c2 = await web3_c2.eth.getAccounts();
        
        const registry = new web3_c1.eth.Contract(
            VCRegistry.abi,
            VCRegistry.networks['1337'].address
        );
        const verifier = new web3_c2.eth.Contract(
            SPVVerifier.abi, 
            SPVVerifier.networks['1338'].address
        );

        console.log('1. Creating mock tokenization transaction on Chain 1...');
        
        // Create a mock token transfer to simulate RWA tokenization
        //this will be the tokenization transaction in the actual implementation
        const mockTokenTx = await web3_c1.eth.sendTransaction({
            from: accounts_c1[0],
            to: accounts_c1[1],
            value: web3_c1.utils.toWei('0.1', 'ether'),
            gas: 21000
        });
        console.log('Mock tokenization tx:', mockTokenTx.transactionHash);

        console.log('2. Computing commitment values...');
        
        // Use the tokenization transaction hash
        const txHash = mockTokenTx.transactionHash;

        // Use DID from VC as asset identifier
        const assetId = web3_c1.utils.keccak256(web3_c1.utils.encodePacked(
            issuedVC.credentialSubject.asset.assetId  // assetId of the asset
        ));

        // Hash the entire VC for credential digest
        const credDigest = web3_c1.utils.keccak256(web3_c1.utils.encodePacked(
            JSON.stringify(issuedVC)
        ));

        // Token binding from the VC
        const tokenBinding = web3_c1.utils.keccak256(web3_c1.utils.encodePacked(
            issuedVC.credentialSubject.asset.tokenBinding.chain,
            issuedVC.credentialSubject.asset.tokenBinding.contract,
            issuedVC.credentialSubject.asset.tokenBinding.tokenId
        ));

        // Current epoch and random nonce
        const epoch = Math.floor(Date.now() / 1000);
        const nonce = web3_c1.utils.randomHex(32);

        console.log('3. Registering commitment on Chain 1...');
        console.log('- Asset ID:', assetId);
        console.log('- Credential Digest:', credDigest);
        
        // Register commitment using the tokenization transaction
        const commitTx = await registry.methods.registerCommitment(
            txHash,
            assetId,
            credDigest,
            tokenBinding,
            epoch,
            nonce
        ).send({ 
            from: accounts_c1[0],
            gas: 500000
        });
        console.log('Commitment registered in tx:', commitTx.transactionHash);

        console.log('4. Generating SPV proof...');
        
        // Get the block containing our commitment
        const block = await web3_c1.eth.getBlock(commitTx.blockNumber);
        const txs = block.transactions;

        // Create merkle tree from all transactions in the block
        const leaves = txs.map((tx, i) => {
            return web3_c1.utils.keccak256(
                web3_c1.eth.abi.encodeParameters(
                    ['bytes32', 'uint256'],
                    [tx, i]
                )
            );
        });
        const tree = new MerkleTree(leaves, web3_c1.utils.keccak256, { sortPairs: true });
        const root = tree.getHexRoot();
        
        // Update block root in registry
        await registry.methods.updateBlockRoot(
            block.number,
            root
        ).send({ 
            from: accounts_c1[0],
            gas: 200000
        });
        console.log('Block root updated on Chain 1:', root);

        // Generate merkle proof for our commitment transaction
        const txIndex = txs.indexOf(commitTx.transactionHash);
        const leaf = web3_c1.utils.keccak256(
            web3_c1.eth.abi.encodeParameters(
                ['bytes32', 'uint256'],
                [commitTx.transactionHash, txIndex]
            )
        );
        const proof = tree.getHexProof(leaf);

        console.log('5. Cross-chain verification on Chain 2...');
        
        // Update trusted header on Chain 2
        //In the actual implementation, this will use oracle to update the trusted header
        await verifier.methods.updateTrustedHeader(
            block.number,
            root
        ).send({ 
            from: accounts_c2[0],
            gas: 200000
        });
        console.log('Trusted header updated on Chain 2');

        // Verify SPV proof
        const spvResult = await verifier.methods.verifyTx(
            commitTx.transactionHash,
            block.number,
            proof,
            txIndex
        ).call();
        console.log('SPV proof verification:', spvResult);
        
        // Verify commitment content matches
        const contentValid = await registry.methods.verifyCommitment(
            txHash,
            assetId,
            credDigest
        ).call();
        console.log('Commitment content verification:', contentValid);

        // Final verification result
        console.log('Final verification result:', spvResult && contentValid ? 'VALID' : 'INVALID');

    } catch (error) {
        console.error('Error:', error);
        if (error.receipt) {
            console.error('Transaction receipt:', error.receipt);
        }
    }
}

demo();