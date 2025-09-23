module.exports = {
  networks: {
    chain1: {
      host: "127.0.0.1",
      port: 8545,
      network_id: "1337",
    },
    chain2: {
      host: "127.0.0.1", 
      port: 8546,
      network_id: "1338",
    }
  },
  compilers: {
    solc: {
      version: "0.8.19",
      settings: {
        optimizer: {
          enabled: true,
          runs: 200
        }
      }
    }
  }
};
