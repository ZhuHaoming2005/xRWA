// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

contract SPVVerifier {
    // Trusted block headers from source chain (C1)
    mapping(uint256 => bytes32) public trustedHeaders;
    
    // Events
    event HeaderUpdated(uint256 indexed blockNumber, bytes32 merkleRoot);
    event ProofVerified(bytes32 indexed txHash, bool success);

    // Update trusted header from source chain
    //In the actual implementation, this will use oracle to get the trusted header
    function updateTrustedHeader(uint256 blockNumber, bytes32 merkleRoot) external {
        require(trustedHeaders[blockNumber] == bytes32(0), "Header exists");
        trustedHeaders[blockNumber] = merkleRoot;
        emit HeaderUpdated(blockNumber, merkleRoot);
    }

    // Verify SPV proof for a transaction
    function verifyTx(
        bytes32 txHash,
        uint256 blockNumber,
        bytes32[] calldata merkleProof,
        uint256 index
    ) external returns (bool) {
        bytes32 root = trustedHeaders[blockNumber];
        require(root != bytes32(0), "Unknown block");

        // Verify merkle proof
        bool isValid = MerkleProof.verify(
            merkleProof,
            root,
            _computeLeaf(txHash, index)
        );

        emit ProofVerified(txHash, isValid);
        return isValid;
    }

    // Compute leaf node for merkle tree
    function _computeLeaf(bytes32 txHash, uint256 index) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(txHash, index));
    }
}