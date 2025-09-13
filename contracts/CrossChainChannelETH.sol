// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title Cross-Chain Channel Contract for ETH
 * @notice This contract implements one side of a cross-chain channel using HTLC
 * @dev This contract can be either buyer side or seller side
 */
contract CrossChainChannelETH is ReentrancyGuard {
    struct Channel {
        address participant;      // The channel opener (depositor)
        address counterparty;    // The other party in the channel
        uint256 deposit;         // Total amount deposited by participant
        uint256 locked;          // Amount locked for counterparty
        uint256 nonce;           // Current state nonce
        bool isBuyer;           // True if this is buyer's contract
        bool isOpen;            // Channel state
        bytes32 hashlock;       // Hash lock for HTLC
        uint256 timelock;       // Time lock for HTLC
        bytes32 preimage;       // Preimage for HTLC
    }

    struct UpdateData {
        bytes32 channelId;
        uint256 nonce;
        uint256[] buyerAssets;   // Support array for future ERC721 compatibility
        uint256[] sellerAssets;  // Support array for future ERC721 compatibility
        bytes buyerSig;
        bytes sellerSig;
    }

    modifier isOpen(bytes32 channelId) {
        require(channels[channelId].isOpen, "Channel not open");
        _;
    }

    // Mapping from channelId to Channel
    mapping(bytes32 => Channel) public channels;

    // Events
    event ChannelOpened(bytes32 indexed channelId, address indexed participant, address indexed counterparty, uint256 deposit);
    event ChannelUpdated(bytes32 indexed channelId, uint256 nonce, uint256 locked);
    event AssetsLocked(bytes32 indexed channelId, bytes32 hashlock, uint256 timelock);
    event AssetsUnlocked(bytes32 indexed channelId, bytes32 preimage);
    event AssetsRefunded(bytes32 indexed channelId);
    event ChannelClosed(bytes32 indexed channelId);

    /**
     * @notice Opens a new channel
     * @param counterparty Address of the other party
     * @param isBuyer Whether this contract is for buyer
     * @return channelId The ID of the created channel
     */
    function openChannel(address counterparty, bool isBuyer, bytes32 channelId) external payable nonReentrant returns (bytes32) {
        require(msg.value > 0, "Deposit required");
        require(counterparty != address(0), "Invalid counterparty");
        require(counterparty != msg.sender, "Cannot open channel with self");
        require(!channels[channelId].isOpen, "Channel already exists");

        channels[channelId] = Channel({
            participant: msg.sender,
            counterparty: counterparty,
            deposit: msg.value,
            locked: 0,
            nonce: 0,
            isBuyer: isBuyer,
            isOpen: true,
            hashlock: bytes32(0),
            timelock: 0,
            preimage: bytes32(0)
        });

        emit ChannelOpened(channelId, msg.sender, counterparty, msg.value);
        return channelId;
    }

    /**
     * @notice Updates channel state with signed messages from both parties
     * @param update The update data containing signatures and new state
     */
    function updateChannel(UpdateData calldata update) external isOpen(update.channelId) {
        Channel storage channel = channels[update.channelId];
        require(update.nonce > channel.nonce, "Invalid nonce");
        require(channel.hashlock == bytes32(0), "Assets already locked");
        require(msg.sender == channel.participant || msg.sender == channel.counterparty, "Unauthorized");
        
        // Verify signatures
        bytes32 messageHash = keccak256(
            abi.encode(
                update.channelId,
                update.nonce,
                update.buyerAssets,
                update.sellerAssets
            )
        );
        
        require(_verifySignature(messageHash, update.buyerSig, channel.isBuyer ? channel.participant : channel.counterparty), "Invalid buyer signature");
        require(_verifySignature(messageHash, update.sellerSig, channel.isBuyer ? channel.counterparty : channel.participant), "Invalid seller signature");

        // Update state based on contract type
        uint256 newLocked;
        if (channel.isBuyer) {
            require(update.buyerAssets.length == 1, "Invalid buyer assets format for ETH");
            newLocked = update.buyerAssets[0];
        } else {
            require(update.sellerAssets.length == 1, "Invalid seller assets format for ETH");
            newLocked = update.sellerAssets[0];
        }

        require(newLocked <= channel.deposit, "Insufficient funds");
        
        channel.locked = newLocked;
        channel.nonce = update.nonce;

        emit ChannelUpdated(update.channelId, update.nonce, newLocked);
    }

    /**
     * @notice Locks assets with HTLC
     * @param channelId The channel identifier
     * @param hashlock The hash lock
     * @param timelock The time lock
     */
    function lock(bytes32 channelId, bytes32 hashlock, uint256 timelock) external isOpen(channelId) {
        Channel storage channel = channels[channelId];
        require(channel.hashlock == bytes32(0), "Assets already locked");
        require(timelock > block.timestamp, "Invalid timelock");
        require(msg.sender == channel.participant, "Unauthorized");

        channel.hashlock = hashlock;
        channel.timelock = timelock;

        emit AssetsLocked(channelId, hashlock, timelock);
    }

    /**
     * @notice Unlocks assets by providing preimage
     * @param channelId The channel identifier
     * @param preimage The preimage of the hashlock
     */
    function unlock(bytes32 channelId, bytes32 preimage) external nonReentrant isOpen(channelId) {
        Channel storage channel = channels[channelId];
        require(channel.hashlock != bytes32(0), "No active lock");
        require(msg.sender == channel.counterparty, "Unauthorized");
        require(block.timestamp <= channel.timelock, "Lock expired");
        require(keccak256(abi.encodePacked(preimage)) == channel.hashlock, "Invalid preimage");

        uint256 amount = channel.locked;
        channel.deposit -= amount;
        channel.hashlock = bytes32(0);
        channel.timelock = 0;
        channel.locked = 0;
        channel.preimage = preimage;
        payable(channel.counterparty).transfer(amount);
        emit AssetsUnlocked(channelId, preimage);
    }

    /**
     * @notice Refunds locked assets after timeout
     * @param channelId The channel identifier
     */
    function refund(bytes32 channelId) external isOpen(channelId) {
        Channel storage channel = channels[channelId];
        require(msg.sender == channel.participant, "Unauthorized");
        require(channel.hashlock != bytes32(0), "No active lock");
        require(block.timestamp > channel.timelock, "Lock not expired");

        channel.hashlock = bytes32(0);
        channel.timelock = 0;
        channel.locked = 0;

        emit AssetsRefunded(channelId);
    }

    /**
     * @notice Closes the channel and settles final balances
     * @param channelId The channel identifier
     */
    function closeChannel(bytes32 channelId) external nonReentrant isOpen(channelId) {
        Channel storage channel = channels[channelId];
        require(msg.sender == channel.participant, "Only participant can close");
        require(channel.hashlock == bytes32(0) || block.timestamp > channel.timelock, "Active lock exists");

        uint256 remaining = channel.deposit;
        channel.isOpen = false;
        channel.deposit = 0;

        if (remaining > 0) {
            payable(channel.participant).transfer(remaining);
        }

        emit ChannelClosed(channelId);
    }

    /**
     * @notice Verifies signature of a message
     * @param messageHash The hash of the message
     * @param signature The signature to verify
     * @param signer The expected signer
     * @return bool True if signature is valid
     */
    function _verifySignature(bytes32 messageHash, bytes memory signature, address signer) internal pure returns (bool) {
        bytes32 ethSignedMessageHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash)
        );
        
        (bytes32 r, bytes32 s, uint8 v) = _splitSignature(signature);
        address recoveredSigner = ecrecover(ethSignedMessageHash, v, r, s);
        
        return recoveredSigner == signer;
    }

    /**
     * @notice Splits signature into r, s, v components
     * @param sig The signature to split
     * @return r The r component of the signature
     * @return s The s component of the signature
     * @return v The v component of the signature
     */
    function _splitSignature(bytes memory sig) internal pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(sig.length == 65, "Invalid signature length");

        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }

        if (v < 27) {
            v += 27;
        }

        require(v == 27 || v == 28, "Invalid signature v value");
    }
}