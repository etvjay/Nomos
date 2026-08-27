export const BRADBURY = {
  id: 4221,
  rpc: 'https://rpc-bradbury.genlayer.com/api',
  contracts: {
    ppa: '0xe4d3f0b1119f940c5e98bc3899a595a92c988f7a',
    sda: '0xTBD_SELF_DRIVING_ACCOUNT', // deploy next: apps/showcase/contracts/self_driving_account.py
    claimVerification: '0x',
    claimEncumbrance: '0x',
  }
} as const;

// Minimal PPA ABI surface used by showcase (genlayer-js expects full ABI; frontend uses viem read stubs)
// Real writes go via genlayer-js; this file only holds addresses + chain.
