export const BRADBURY = {
  id: 4221,
  rpc: 'https://rpc-bradbury.genlayer.com/api',
  contracts: {
    ppa: '0xe4d3f0b1119f940c5e98bc3899a595a92c988f7a',
    sdaPrice: '0xTBD_SDA_PRICE', // contracts/sda_price.py
    sdaSla: '0xTBD_SDA_SLA',     // contracts/sda_sla.py
    sda: '0xTBD_SELF_DRIVING_ACCOUNT', // legacy combined (deprecated split)
    claimVerification: '0x',
    claimEncumbrance: '0x',
  }
} as const;

// Minimal PPA ABI surface used by showcase (genlayer-js expects full ABI; frontend uses viem read stubs)
// Real writes go via genlayer-js; this file only holds addresses + chain.
