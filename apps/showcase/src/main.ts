import { BRADBURY } from './config';

type Tab = 'send' | 'watch' | 'invoice';

function $(id: string) { return document.getElementById(id)!; }

function setTab(t: Tab) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-tab="${t}"]`)!.classList.add('active');
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  $(`view-${t}`).classList.add('active');
}

function log(el: HTMLElement, msg: string) {
  const ts = new Date().toISOString().slice(11,19);
  el.textContent = `[${ts}] ${msg}\n` + el.textContent;
}

 // tabs
document.querySelectorAll('.tab').forEach(b => {
  b.addEventListener('click', () => setTab((b as HTMLElement).dataset.tab as Tab));
});

// wallet (read-only scaffold; real GenLayer signer wiring is milestone 2)
let wallet: string | null = null;
$('connectBtn').addEventListener('click', async () => {
  // @ts-ignore
  const eth = (window as any).ethereum;
  if (!eth) { alert('No wallet found. Install MetaMask and switch to GenLayer Bradbury 4221.'); return; }
  try {
    const accs: string[] = await eth.request({ method: 'eth_requestAccounts' });
    wallet = accs[0] ?? null;
    $('walletAddr').textContent = wallet ?? 'not connected';
    log($('sendLog'), `connected ${wallet}`);
  } catch (e: any) { log($('sendLog'), `connect failed: ${e?.message ?? e}`); }
});

$('ppaAddr').textContent = BRADBURY.contracts.ppa;

// App1 — Send with Rules (wired to log + trace; onchain calls land in next commit)
$('btnCreateAccount').addEventListener('click', () => {
  const id = ($('sendAccount') as HTMLInputElement).value.trim();
  const allow = ($('allowlist') as HTMLInputElement).value.trim();
  const perTx = ($('perTx') as HTMLInputElement).value;
  const daily = ($('dailyCap') as HTMLInputElement).value;
  $('sendTrace').textContent = `create_account(${id}) policy={ allowlist:[${allow || 'any'}] perTx:${perTx} daily:${daily} } — next: deposit → send`;
  log($('sendLog'), `create/update ${id} policy perTx=${perTx} daily=${daily} allowlist=${allow || '(open)'}`);
});
$('btnDeposit').addEventListener('click', () => {
  const id = ($('sendAccount') as HTMLInputElement).value.trim();
  $('sendTrace').textContent = `deposit(${id}, 3000) → capital_commitment +3000`;
  log($('sendLog'), `deposit 3000 → ${id} (stub — onchain in App1 build)`);
});
$('btnSend').addEventListener('click', () => {
  const to = ($('sendTo') as HTMLInputElement).value.trim();
  const amt = ($('sendAmount') as HTMLInputElement).value;
  $('sendTrace').textContent = `send → policy ✓ → encumbrance ✓ → claim ✓ → settle ✓\nto ${to || '(set recipient)'} amount ${amt}`;
  log($('sendLog'), `send ${amt} → ${to || '(no recipient)'} (gated — stub)`);
});

// App2
$('btnWatch').addEventListener('click', () => {
  const url = ($('watchUrl') as HTMLInputElement).value;
  $('watchTrace').textContent = `evaluate(${url}) → validators: web.render + LLM → verdict VERIFIED (sim)`;
  log($('watchLog'), `evaluate ${url} — simulated VERIFIED`);
});
$('btnWatchPay').addEventListener('click', () => {
  const amt = ($('watchAmount') as HTMLInputElement).value;
  const to = ($('watchPayTo') as HTMLInputElement).value;
  $('watchTrace').textContent = `watch → VERIFIED → gated pay ${amt} → ${to || '(recipient)'}: policy → encumbrance → settle`;
  log($('watchLog'), `watch→pay ${amt} → ${to || '(recipient)'} (stub)`);
});

// App3
$('btnVerify').addEventListener('click', () => {
  const n = ($('invNumber') as HTMLInputElement).value;
  const a = ($('invAmount') as HTMLInputElement).value;
  $('invoiceTrace').textContent = `verify_claim(${n}, ${a}) → VERIFIED (sim)`;
  log($('invoiceLog'), `verify ${n} amount=${a} → VERIFIED (sim)`);
});
$('btnReserve').addEventListener('click', () => {
  $('invoiceTrace').textContent = `if VERIFIED → reserve → financeable_balance unchanged, active_encumbrances +`;
  log($('invoiceLog'), `reserve (stub — requires VERIFIED)`);
});
$('btnInvSettle').addEventListener('click', () => {
  $('invoiceTrace').textContent = `settle → ppa.send via gated pipeline`;
  log($('invoiceLog'), `settle (stub)`);
});

// smoke: build must succeed
console.log('Nomos showcase shell ready', BRADBURY.id);
