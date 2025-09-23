const VCRegistry = artifacts.require("VCRegistry");
const SPVVerifier = artifacts.require("SPVVerifier");

module.exports = async function(deployer, network) {
  // Deploy VCRegistry on chain1
  if (network === 'chain1') {
    await deployer.deploy(VCRegistry);
  }
  // Deploy SPVVerifier on chain2
  else if (network === 'chain2') {
    await deployer.deploy(SPVVerifier);
  }
};
