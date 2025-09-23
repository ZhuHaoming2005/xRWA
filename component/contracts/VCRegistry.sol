// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

contract VCRegistry {
    // VC commitment structure
    struct VCCommitment {
        bytes32 assetId;      // Asset identifier
        bytes32 credDigest;   // Hash of credential fields
        bytes32 tokenBinding; // Chain/contract/token binding
        uint256 epoch;       // Validity epoch
        bytes32 nonce;       // Unique nonce
        bool isRevoked;      // Revocation status
    }

    // Mapping from tx hash to commitment
    mapping(bytes32 => VCCommitment) public commitments;
    
    // Merkle root of the block containing commitments
    mapping(uint256 => bytes32) public blockRoots;
    
    // Events
    event CommitmentRegistered(
        bytes32 indexed txHash,
        bytes32 indexed assetId,
        bytes32 credDigest
    );
    
    event BlockRootUpdated(uint256 indexed blockNumber, bytes32 root);

    // Custom errors
    error CommitmentExists();
    error CommitmentNotFound();
    error RootExists();
    error InvalidCommitment();

    // Register a new VC commitment
    function registerCommitment(
        bytes32 txHash,
        bytes32 assetId,
        bytes32 credDigest,
        bytes32 tokenBinding,
        uint256 epoch,
        bytes32 nonce
    ) external {
        if (commitments[txHash].assetId != bytes32(0)) revert CommitmentExists();
        
        commitments[txHash] = VCCommitment({
            assetId: assetId,
            credDigest: credDigest,
            tokenBinding: tokenBinding,
            epoch: epoch,
            nonce: nonce,
            isRevoked: false
        });

        emit CommitmentRegistered(txHash, assetId, credDigest);
    }

    // Update block's Merkle root (called by block finalizer)
    function updateBlockRoot(uint256 blockNumber, bytes32 root) external {
        if (blockRoots[blockNumber] != bytes32(0)) revert RootExists();
        if (root == bytes32(0)) revert InvalidCommitment();
        
        blockRoots[blockNumber] = root;
        emit BlockRootUpdated(blockNumber, root);
    }

    // Revoke a commitment
    function revokeCommitment(bytes32 txHash) external {
        if (commitments[txHash].assetId == bytes32(0)) revert CommitmentNotFound();
        commitments[txHash].isRevoked = true;
    }

    // Verify commitment exists and matches credential
    function verifyCommitment(
        bytes32 txHash,
        bytes32 assetId,
        bytes32 credDigest
    ) external view returns (bool) {
        VCCommitment memory comm = commitments[txHash];
        return (
            comm.assetId == assetId &&
            comm.credDigest == credDigest &&
            !comm.isRevoked
        );
    }
}