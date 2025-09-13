const { soliditySha3 } = require('web3-utils');
const { randomBytes } = require('crypto');

class SwapHelper {
  // Generate random preimage and its hash for HTLC
  static generatePreimageAndHash() {
    const preimage = '0x' + randomBytes(32).toString('hex');
    const hash = soliditySha3({ t: 'bytes32', v: preimage });
    return { preimage, hash };
  }

  // Calculate timelock (current time + lock duration in seconds)
  static async calculateTimelock(web3, duration = 3600) {
    const block = await web3.eth.getBlock('latest');
    return block.timestamp + duration;
  }

  // Generate channel ID
  static generateChannelId(sender, receiver, nonce) {
    return soliditySha3(
      { t: 'address', v: sender },
      { t: 'address', v: receiver },
      { t: 'uint256', v: nonce }
    );
  }

  // Sign state update
  static async signState(web3, channelId, nonce, buyerAssets, sellerAssets, signer) {
    const encodedData = web3.eth.abi.encodeParameters(
      ['bytes32', 'uint256', 'uint256[]', 'uint256[]'],
      [channelId, nonce, buyerAssets, sellerAssets]
    );
    
    const messageHash = web3.utils.keccak256(encodedData);
    
    const signature = await web3.eth.sign(messageHash, signer);
    return signature;
  }

  // Helper to wait for specific time
  static async increaseTime(web3, seconds) {
    return new Promise((resolve, reject) => {
      web3.currentProvider.send({
        jsonrpc: '2.0',
        method: 'evm_increaseTime',
        params: [seconds],
        id: new Date().getTime()
      }, (err, result) => {
        if (err) {
          reject(err);
          return;
        }
        
        web3.currentProvider.send({
          jsonrpc: '2.0',
          method: 'evm_mine',
          params: [],
          id: new Date().getTime()
        }, (err2, result2) => {
          if (err2) {
            reject(err2);
          } else {
            resolve(result2);
          }
        });
      });
    });
  }
}

module.exports = SwapHelper;
