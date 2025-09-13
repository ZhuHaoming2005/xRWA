const CrossChainChannelERC20 = artifacts.require("CrossChainChannelERC20");
const CrossChainChannelERC721 = artifacts.require("CrossChainChannelERC721");
const TestToken = artifacts.require("TestToken");
const TestNFT = artifacts.require("TestNFT");
const SwapHelper = require('./helpers/SwapHelper');

contract('ERC20 to ERC721 Swap', (accounts) => {
  const [buyer, seller] = accounts;
  const tokenAmount = web3.utils.toWei('100', 'ether');
  const tokenId = 1;
  
  let erc20Channel;
  let erc721Channel;
  let testToken;
  let testNFT;
  let channelId;
  let htlc;

  before(async () => {
    // Deploy contracts
    erc20Channel = await CrossChainChannelERC20.new();
    erc721Channel = await CrossChainChannelERC721.new();
    testToken = await TestToken.new();
    testNFT = await TestNFT.new();

    // Mint tokens for buyer
    await testToken.mint(buyer, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: buyer });

    // Mint NFT for seller
    await testNFT.mintSpecific(seller, tokenId);
    await testNFT.approve(erc721Channel.address, tokenId, { from: seller });
  });

  it('should execute ERC20 to ERC721 atomic swap', async () => {
    // Generate HTLC parameters
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3);
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());

    console.log('Step 1: Buyer opens ERC20 channel');
    await erc20Channel.openChannel(
      seller,
      testToken.address,
      tokenAmount,
      true,
      channelId,
      { from: buyer }
    );

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
    const buyerAssets = [tokenAmount];
    const sellerAssets = [tokenId];

    // Sign state updates
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

    // Update both channels
    await erc20Channel.updateChannel({
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

    console.log('Step 4: Lock assets with HTLC');
    await erc20Channel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc721Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    console.log('Step 5: Unlock assets with preimage');
    await erc721Channel.unlock(channelId, htlc.preimage, { from: buyer });
    await erc20Channel.unlock(channelId, htlc.preimage, { from: seller });

    // Verify final ownership
    const nftOwner = await testNFT.ownerOf(tokenId);
    const sellerTokenBalance = await testToken.balanceOf(seller);
    
    assert.equal(nftOwner, buyer, 'Buyer should own the NFT');
    assert.equal(
      sellerTokenBalance.toString(),
      tokenAmount,
      'Seller should receive tokens'
    );
    console.log('Swap completed successfully');
  });

  it('should handle refund after timeout', async () => {
    // Mint new tokens and NFT
    const newTokenId = 2;
    await testToken.mint(buyer, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: buyer });
    await testNFT.mintSpecific(seller, newTokenId);
    await testNFT.approve(erc721Channel.address, newTokenId, { from: seller });

    // Generate new channel ID and HTLC parameters
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 3600); // 1 hour timelock

    // Open channels
    await erc20Channel.openChannel(
      seller,
      testToken.address,
      tokenAmount,
      true,
      channelId,
      { from: buyer }
    );
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
    const buyerAssets = [tokenAmount];
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

    await erc20Channel.updateChannel({
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

    await erc20Channel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc721Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    // Increase time to simulate timeout
    await SwapHelper.increaseTime(web3, 7200); // Advance 2 hours

    // Refund assets
    await erc20Channel.refund(channelId, { from: buyer });
    await erc721Channel.refund(channelId, { from: seller });

    // Close channels
    await erc20Channel.closeChannel(channelId, { from: buyer });
    await erc721Channel.closeChannel(channelId, { from: seller });

    // Verify ownership after refund
    const nftOwner = await testNFT.ownerOf(newTokenId);
    const buyerTokenBalance = await testToken.balanceOf(buyer);
    
    assert.equal(nftOwner, seller, 'Seller should still own the NFT after refund');
    assert.isTrue(
      web3.utils.toBN(buyerTokenBalance).gte(web3.utils.toBN(tokenAmount)),
      'Buyer should have at least the expected amount of tokens refunded'
    );
    console.log('Refund scenario completed successfully');
  });

  it('should handle channel closure without active lock', async () => {
    // Mint new tokens and NFT
    const newTokenId = 3;
    await testToken.mint(buyer, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: buyer });
    await testNFT.mintSpecific(seller, newTokenId);
    await testNFT.approve(erc721Channel.address, newTokenId, { from: seller });

    // Generate new channel ID
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());

    console.log('Step 1: Open channels');
    await erc20Channel.openChannel(
      seller,
      testToken.address,
      tokenAmount,
      true,
      channelId,
      { from: buyer }
    );
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
    const buyerAssets = [tokenAmount];
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

    await erc20Channel.updateChannel({
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
    await erc20Channel.closeChannel(channelId, { from: buyer });
    await erc721Channel.closeChannel(channelId, { from: seller });

    // Verify channels are closed
    const erc20ChannelData = await erc20Channel.channels(channelId);
    const erc721ChannelData = await erc721Channel.channels(channelId);

    assert.equal(erc20ChannelData.isOpen, false, 'ERC20 channel should be closed');
    assert.equal(erc721ChannelData.isOpen, false, 'ERC721 channel should be closed');

    console.log('Channel closure completed successfully');
  });

  it('should handle channel closure with expired lock', async () => {
    // Mint new tokens and NFT
    const newTokenId = 4;
    await testToken.mint(buyer, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: buyer });
    await testNFT.mintSpecific(seller, newTokenId);
    await testNFT.approve(erc721Channel.address, newTokenId, { from: seller });

    // Generate new channel ID and HTLC parameters
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 60); // 1 minute timelock

    console.log('Step 1: Open channels and lock assets');
    await erc20Channel.openChannel(
      seller,
      testToken.address,
      tokenAmount,
      true,
      channelId,
      { from: buyer }
    );
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
    const buyerAssets = [tokenAmount];
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

    await erc20Channel.updateChannel({
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

    await erc20Channel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc721Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    // Increase time to make lock expired
    await SwapHelper.increaseTime(web3, 120); // Advance 2 minutes

    console.log('Step 2: Close channels with expired lock');
    await erc20Channel.closeChannel(channelId, { from: buyer });
    await erc721Channel.closeChannel(channelId, { from: seller });

    // Verify channels are closed
    const erc20ChannelData = await erc20Channel.channels(channelId);
    const erc721ChannelData = await erc721Channel.channels(channelId);

    assert.equal(erc20ChannelData.isOpen, false, 'ERC20 channel should be closed');
    assert.equal(erc721ChannelData.isOpen, false, 'ERC721 channel should be closed');

    console.log('Channel closure with expired lock completed successfully');
  });
});
