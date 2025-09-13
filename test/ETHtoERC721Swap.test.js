const CrossChainChannelETH = artifacts.require("CrossChainChannelETH");
const CrossChainChannelERC721 = artifacts.require("CrossChainChannelERC721");
const TestNFT = artifacts.require("TestNFT");
const SwapHelper = require('./helpers/SwapHelper');

contract('ETH to ERC721 Swap', (accounts) => {
  const [buyer, seller] = accounts;
  const ethAmount = web3.utils.toWei('1', 'ether');
  const tokenId = 1;
  
  let ethChannel;
  let erc721Channel;
  let testNFT;
  let channelId;
  let htlc;

  before(async () => {
    // Deploy contracts
    ethChannel = await CrossChainChannelETH.new();
    erc721Channel = await CrossChainChannelERC721.new();
    testNFT = await TestNFT.new();

    // Mint NFT for seller
    await testNFT.mintSpecific(seller, tokenId);
    await testNFT.approve(erc721Channel.address, tokenId, { from: seller });
  });

  it('should execute ETH to ERC721 atomic swap', async () => {
    // Generate HTLC parameters
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 3600);
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());

    console.log('Step 1: Buyer opens ETH channel');
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });

    console.log('Step 2: Seller opens ERC721 channel');
    await erc721Channel.openChannel(
      buyer,
      testNFT.address,
      [tokenId],
      false,
      channelId,
      { from: seller }
    );

    console.log('Step 3: Update channels with agreed assets');
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [tokenId];

    // Sign state updates
    const buyerSigETH = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyer
    );
    const sellerSigETH = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      seller
    );

    // Update both channels
    await ethChannel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig: buyerSigETH,
      sellerSig: sellerSigETH
    });

    await erc721Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig: buyerSigETH,
      sellerSig: sellerSigETH
    });

    console.log('Step 4: Lock assets with HTLC');
    await ethChannel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc721Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    console.log('Step 5: Unlock assets with preimage');
    await erc721Channel.unlock(channelId, htlc.preimage, { from: buyer });
    await ethChannel.unlock(channelId, htlc.preimage, { from: seller });

    // Verify final ownership
    const nftOwner = await testNFT.ownerOf(tokenId);
    assert.equal(nftOwner, buyer, 'Buyer should own the NFT');
    console.log('Swap completed successfully');
  });

  it('should handle refund after timeout', async () => {
    // Mint new NFT for seller
    const newTokenId = 2;
    await testNFT.mintSpecific(seller, newTokenId);
    await testNFT.approve(erc721Channel.address, newTokenId, { from: seller });

    // Generate new channel ID and HTLC parameters
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 3600); // 1 hour timelock

    // Open channels and lock assets
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });
    await erc721Channel.openChannel(
      buyer,
      testNFT.address,
      [newTokenId],
      false,
      channelId,
      { from: seller }
    );

    // Update and lock assets
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [newTokenId];

    const buyerSig = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyer
    );
    const sellerSig = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      seller
    );

    await ethChannel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await erc721Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await ethChannel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc721Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    // Increase time to simulate timeout
    await SwapHelper.increaseTime(web3, 7200); // Advance 2 hours

    // Refund assets
    await ethChannel.refund(channelId, { from: buyer });
    await erc721Channel.refund(channelId, { from: seller });

    // Close channels
    await ethChannel.closeChannel(channelId, { from: buyer });
    await erc721Channel.closeChannel(channelId, { from: seller });

    // Verify NFT ownership after refund
    const nftOwner = await testNFT.ownerOf(newTokenId);
    assert.equal(nftOwner, seller, 'Seller should still own the NFT after refund');
    console.log('Refund scenario completed successfully');
  });

  it('should handle channel closure without active lock', async () => {
    // Mint new NFT for seller
    const newTokenId = 3;
    await testNFT.mintSpecific(seller, newTokenId);
    await testNFT.approve(erc721Channel.address, newTokenId, { from: seller });

    // Generate new channel ID
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());

    console.log('Step 1: Open channels');
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });
    await erc721Channel.openChannel(
      buyer,
      testNFT.address,
      [newTokenId],
      false,
      channelId,
      { from: seller }
    );

    console.log('Step 2: Update channel state');
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [newTokenId];

    const buyerSig = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyer
    );
    const sellerSig = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      seller
    );

    await ethChannel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await erc721Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    console.log('Step 3: Close channels');
    
    // Record balances and ownership before closing
    const buyerEthBalanceBefore = await web3.eth.getBalance(buyer);
    const nftOwnerBefore = await testNFT.ownerOf(newTokenId);
    
    // Check channel state before closing
    const ethChannelDataBefore = await ethChannel.channels(channelId);
    const erc721ChannelDataBefore = await erc721Channel.channels(channelId);
    
    await ethChannel.closeChannel(channelId, { from: buyer });
    await erc721Channel.closeChannel(channelId, { from: seller });

    // Verify channels are closed
    const ethChannelData = await ethChannel.channels(channelId);
    const erc721ChannelData = await erc721Channel.channels(channelId);

    assert.equal(ethChannelData.isOpen, false, 'ETH channel should be closed');
    assert.equal(erc721ChannelData.isOpen, false, 'ERC721 channel should be closed');

    // Verify assets are returned
    const buyerEthBalanceAfter = await web3.eth.getBalance(buyer);
    const nftOwnerAfter = await testNFT.ownerOf(newTokenId);
    
    // ETH should be returned to buyer (accounting for gas costs)
    assert.isTrue(
      web3.utils.toBN(buyerEthBalanceAfter).gte(web3.utils.toBN(buyerEthBalanceBefore)),
      'Buyer should receive ETH back (or at least not lose ETH due to gas)'
    );
    
    // NFT should be returned to seller (from contract to seller)
    assert.equal(nftOwnerAfter, seller, 'Seller should receive NFT back');
    assert.equal(nftOwnerBefore, erc721Channel.address, 'NFT should be in contract before closing');

    console.log('Channel closure completed successfully');
  });

  it('should handle channel closure with expired lock', async () => {
    // Mint new NFT for seller
    const newTokenId = 4;
    await testNFT.mintSpecific(seller, newTokenId);
    await testNFT.approve(erc721Channel.address, newTokenId, { from: seller });

    // Generate new channel ID and HTLC parameters
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 60); // 1 minute timelock

    console.log('Step 1: Open channels and lock assets');
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });
    await erc721Channel.openChannel(
      buyer,
      testNFT.address,
      [newTokenId],
      false,
      channelId,
      { from: seller }
    );

    // Update and lock assets
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [newTokenId];

    const buyerSig = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyer
    );
    const sellerSig = await SwapHelper.signState(
      web3,
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      seller
    );

    await ethChannel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await erc721Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await ethChannel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc721Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    // Increase time to make lock expired
    await SwapHelper.increaseTime(web3, 120); // Advance 2 minutes

    console.log('Step 2: Close channels with expired lock');
    await ethChannel.closeChannel(channelId, { from: buyer });
    await erc721Channel.closeChannel(channelId, { from: seller });

    // Verify channels are closed
    const ethChannelData = await ethChannel.channels(channelId);
    const erc721ChannelData = await erc721Channel.channels(channelId);

    assert.equal(ethChannelData.isOpen, false, 'ETH channel should be closed');
    assert.equal(erc721ChannelData.isOpen, false, 'ERC721 channel should be closed');

    console.log('Channel closure with expired lock completed successfully');
  });
});
