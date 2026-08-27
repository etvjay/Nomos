export const BRADBURY = {
  id: 4221,
  rpc: 'https://rpc-bradbury.genlayer.com/api',
  contracts: {
    ppa: '0xe4d3f0b1119f940c5e98bc3899a595a92c988f7a',
    sdaPrice: '0x2919860C36BC6f975087be13A3fd4969b710Cc42', // sda_price.py tx c5c5...
    sdaSla: '0xf08Eb73cFf7A1bC2653414d2e1cBc636d5a83028',     // sda_sla.py tx 97f6...
    sda: '0xTBD_SELF_DRIVING_ACCOUNT', // legacy combined (deprecated split)
    claimVerification: '0x',
    claimEncumbrance: '0x',
  }
} as const;

// Minimal PPA ABI surface used by showcase (genlayer-js expects full ABI; frontend uses viem read stubs)
// Real writes go via genlayer-js; this file only holds addresses + chain.
