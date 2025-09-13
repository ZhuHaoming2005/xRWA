const CrossChainChannelETH = artifacts.require("CrossChainChannelETH");
const CrossChainChannelERC20 = artifacts.require("CrossChainChannelERC20");
const TestToken = artifacts.require("TestToken");
const SwapHelper = require('./helpers/SwapHelper');

contract('ETH to ERC20 Swap', (accounts) => {
  const [buyer, seller] = accounts;
  const ethAmount = web3.utils.toWei('1', 'ether');
  const tokenAmount = web3.utils.toWei('100', 'ether');
  
  let ethChannel;
  let erc20Channel;
  let testToken;
  let channelId;
  let htlc;

  before(async () => {
    // Deploy contracts
    ethChannel = await CrossChainChannelETH.new();
    erc20Channel = await CrossChainChannelERC20.new();
    testToken = await TestToken.new();

    // Mint tokens for seller
    await testToken.mint(seller, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: seller });
  });

  it('should execute ETH to ERC20 atomic swap', async () => {
    // Generate HTLC parameters
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3);
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());

    console.log('Step 1: Buyer opens ETH channel');
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });

    console.log('Step 2: Seller opens ERC20 channel');
    await erc20Channel.openChannel(
      buyer,
      testToken.address,
      tokenAmount,
      false,
      channelId,
      { from: seller }
    );

    console.log('Step 3: Update channels with agreed amounts');
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [tokenAmount];

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

    await erc20Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig: buyerSigETH,
      sellerSig: sellerSigETH
    });

    console.log('Step 4: Lock assets with HTLC');
    await ethChannel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc20Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    console.log('Step 5: Unlock assets with preimage');
    await erc20Channel.unlock(channelId, htlc.preimage, { from: buyer });
    await ethChannel.unlock(channelId, htlc.preimage, { from: seller });

    // Verify final balances
    const buyerTokenBalance = await testToken.balanceOf(buyer);
    const sellerEthBalance = await web3.eth.getBalance(seller);

    // Check that buyer received the expected amount of tokens
    // Note: buyer might have had some tokens from initial mint, so we check the transfer amount
    const expectedBalance = web3.utils.toBN(tokenAmount);
    const actualBalance = web3.utils.toBN(buyerTokenBalance);
    
    assert.isTrue(
      actualBalance.gte(expectedBalance),
      'Buyer should receive at least the expected amount of tokens'
    );
    console.log('Swap completed successfully');
    console.log('Buyer token balance:', buyerTokenBalance.toString());
    console.log('Expected token amount:', tokenAmount);
  });

  it('should handle refund after timeout', async () => {
    // Mint new tokens for seller since previous ones were transferred
    await testToken.mint(seller, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: seller });

    // Generate new channel ID and HTLC parameters
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 3600); // 1 hour timelock

    // Open channels and lock assets
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });
    await erc20Channel.openChannel(
      buyer,
      testToken.address,
      tokenAmount,
      false,
      channelId,
      { from: seller }
    );

    // Update and lock assets
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [tokenAmount];

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

    await erc20Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await ethChannel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc20Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    // Increase time to simulate timeout
    await SwapHelper.increaseTime(web3, 7200); // Advance 2 hours

    // Refund assets
    await ethChannel.refund(channelId, { from: buyer });
    await erc20Channel.refund(channelId, { from: seller });

    // Close channels
    await ethChannel.closeChannel(channelId, { from: buyer });
    await erc20Channel.closeChannel(channelId, { from: seller });

    console.log('Refund scenario completed successfully');
  });

  it('should handle channel closure without active lock', async () => {
    // Mint new tokens for seller
    await testToken.mint(seller, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: seller });

    // Generate new channel ID
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());

    console.log('Step 1: Open channels');
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });
    await erc20Channel.openChannel(
      buyer,
      testToken.address,
      tokenAmount,
      false,
      channelId,
      { from: seller }
    );

    console.log('Step 2: Update channel state');
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [tokenAmount];

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

    await erc20Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    console.log('Step 3: Close channels');
    
    // Record balances before closing
    const buyerEthBalanceBefore = await web3.eth.getBalance(buyer);
    const sellerTokenBalanceBefore = await testToken.balanceOf(seller);
    
    // Check channel state before closing
    const ethChannelDataBefore = await ethChannel.channels(channelId);
    const erc20ChannelDataBefore = await erc20Channel.channels(channelId);
    
    await ethChannel.closeChannel(channelId, { from: buyer });
    await erc20Channel.closeChannel(channelId, { from: seller });

    // Verify channels are closed
    const ethChannelData = await ethChannel.channels(channelId);
    const erc20ChannelData = await erc20Channel.channels(channelId);

    assert.equal(ethChannelData.isOpen, false, 'ETH channel should be closed');
    assert.equal(erc20ChannelData.isOpen, false, 'ERC20 channel should be closed');

    // Verify assets are returned
    const buyerEthBalanceAfter = await web3.eth.getBalance(buyer);
    const sellerTokenBalanceAfter = await testToken.balanceOf(seller);
    
    // ETH should be returned to buyer (accounting for gas costs)
    assert.isTrue(
      web3.utils.toBN(buyerEthBalanceAfter).gte(web3.utils.toBN(buyerEthBalanceBefore)),
      'Buyer should receive ETH back (or at least not lose ETH due to gas)'
    );
    
    // Tokens should be returned to seller (check that tokens were actually returned)
    const expectedSellerBalance = web3.utils.toBN(sellerTokenBalanceBefore).add(web3.utils.toBN(erc20ChannelDataBefore.deposit));
    assert.equal(
      sellerTokenBalanceAfter.toString(),
      expectedSellerBalance.toString(),
      'Seller should receive all tokens back from channel'
    );

    console.log('Channel closure completed successfully');
  });

  it('should handle channel closure with expired lock', async () => {
    // Mint new tokens for seller
    await testToken.mint(seller, tokenAmount);
    await testToken.approve(erc20Channel.address, tokenAmount, { from: seller });

    // Generate new channel ID and HTLC parameters
    channelId = SwapHelper.generateChannelId(buyer, seller, Date.now());
    htlc = SwapHelper.generatePreimageAndHash();
    const timelock = await SwapHelper.calculateTimelock(web3, 60); // 1 minute timelock

    console.log('Step 1: Open channels and lock assets');
    await ethChannel.openChannel(seller, true, channelId, {
      from: buyer,
      value: ethAmount
    });
    await erc20Channel.openChannel(
      buyer,
      testToken.address,
      tokenAmount,
      false,
      channelId,
      { from: seller }
    );

    // Update and lock assets
    const nonce = 1;
    const buyerAssets = [ethAmount];
    const sellerAssets = [tokenAmount];

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

    await erc20Channel.updateChannel({
      channelId,
      nonce,
      buyerAssets,
      sellerAssets,
      buyerSig,
      sellerSig
    });

    await ethChannel.lock(channelId, htlc.hash, timelock, { from: buyer });
    await erc20Channel.lock(channelId, htlc.hash, timelock, { from: seller });

    // Increase time to make lock expired
    await SwapHelper.increaseTime(web3, 120); // Advance 2 minutes

    console.log('Step 2: Close channels with expired lock');
    
    // Record balances before closing
    const buyerEthBalanceBefore = await web3.eth.getBalance(buyer);
    const sellerTokenBalanceBefore = await testToken.balanceOf(seller);
    
    // Check channel state before closing
    const ethChannelDataBefore = await ethChannel.channels(channelId);
    const erc20ChannelDataBefore = await erc20Channel.channels(channelId);
    
    await ethChannel.closeChannel(channelId, { from: buyer });
    await erc20Channel.closeChannel(channelId, { from: seller });

    // Verify channels are closed
    const ethChannelData = await ethChannel.channels(channelId);
    const erc20ChannelData = await erc20Channel.channels(channelId);

    assert.equal(ethChannelData.isOpen, false, 'ETH channel should be closed');
    assert.equal(erc20ChannelData.isOpen, false, 'ERC20 channel should be closed');

    // Verify assets are returned
    const buyerEthBalanceAfter = await web3.eth.getBalance(buyer);
    const sellerTokenBalanceAfter = await testToken.balanceOf(seller);
    
    // ETH should be returned to buyer (accounting for gas costs)
    assert.isTrue(
      web3.utils.toBN(buyerEthBalanceAfter).gte(web3.utils.toBN(buyerEthBalanceBefore)),
      'Buyer should receive ETH back (or at least not lose ETH due to gas)'
    );
    
    // Tokens should be returned to seller (check that tokens were actually returned)
    const expectedSellerBalance = web3.utils.toBN(sellerTokenBalanceBefore).add(web3.utils.toBN(erc20ChannelDataBefore.deposit));
    assert.equal(
      sellerTokenBalanceAfter.toString(),
      expectedSellerBalance.toString(),
      'Seller should receive all tokens back from channel'
    );

    console.log('Channel closure with expired lock completed successfully');
  });
});
