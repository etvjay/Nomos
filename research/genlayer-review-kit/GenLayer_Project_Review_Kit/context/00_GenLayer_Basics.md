# GenLayer Basics And SDK Context

GenLayer is an AI-native Layer 1 blockchain for trustless adjudication. Intelligent Contracts are Python contracts that can call LLMs, fetch web data, and reach validator consensus over non-deterministic results through the Equivalence Principle.

## Core Concepts

- Intelligent Contracts are usually Python classes extending `gl.Contract`.
- Validators independently evaluate non-deterministic operations and agree on a meaningful result.
- Comparative Equivalence Principle: validators recompute a result and compare within a defined margin. Good for quantifiable or structured outputs.
- Non-comparative Equivalence Principle: validators check whether the leader output satisfies criteria. Good for qualitative outputs, summaries, judgments, and free-form text.
- The point of consensus is agreement on the meaningful result. Validators that only check shape, length, keywords, or JSON fields do not enforce meaningful consensus.

## Networks And References

- Studio: `studio.genlayer.com`
- Docs: `docs.genlayer.com`
- Portal: GenLayer builder submissions portal.
- Networks: StudioNet, Bradbury, Asimov.
- StudioNet is in-IDE and gasless; 0 GEN cost is expected and not a red flag.

## Real SDK Patterns

Common valid patterns:

- Imports: `from genlayer import *`, `import genlayer as gl`
- Contract base: `class X(gl.Contract):`
- Decorators: `@gl.public.view`, `@gl.public.write`, `@gl.public.write.payable`, `@gl.private`
- Storage: `TreeMap`, `DynArray`, `Array`, `Address`, integer types such as `u256`
- Message context: `gl.message.sender_address`, `gl.message.contract_address`, `gl.message.origin_address`, `gl.message.value`
- LLM: `gl.nondet.exec_prompt(...)`
- Web: `gl.nondet.web.render(...)`, `gl.nondet.web.get(...)`, `post`, `request`
- EP: `gl.eq_principle.strict_eq(fn)`, `gl.eq_principle.prompt_comparative(fn, criteria)`, `gl.eq_principle.prompt_non_comparative(fn, task, criteria)`
- Custom leader/validator flow: `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`
- Transfers: `gl.chain.Account(addr).emit_transfer(value)`
- User errors: `gl.vm.UserError("...")`

## Compatibility Rules

The SDK has changed quickly. Do not reject solely for older but plausible SDK forms when the project is otherwise substantive.

Acceptable older patterns can include:

- `IntelligentContract` as a base class.
- `gl.exec_prompt(...)`, `gl.get_webpage(...)`.
- Older strict/nondet helper forms such as `gl.eq_principle_strict_eq(...)`, `gl.non_det_strict_eq(...)`, or `gl.nondet_strict_eq(...)`.
- Older or missing `Depends` headers such as `py-genlayer:test`, `py-genlayer:latest`, or missing pinned GenVM hash.

Treat these as compatibility/update issues, lower certainty, or targeted `more_info` when needed. Reject only when primitives are fabricated/pseudocode, materially misleading, or the code cannot be reviewed as a real GenLayer project.

## Do Not Misread `run_nondet_unsafe`

`gl.vm.run_nondet_unsafe(...)` is official SDK usage. Do not treat the word `unsafe` as a security flaw by itself.

Review whether:

- the leader function is well-scoped,
- the validator function checks the meaningful result,
- outputs are normalized and bounded,
- the result affects meaningful state, payments, ordering, claims, moderation, or workflow.

## Fake Or Suspicious SDK Patterns

Clearly fake or misleading patterns include:

- `gl.Map()`, `gl.Variable()`, `gl.msg.sender()`, `gl.block.timestamp()`, `gl.transfer(...)`
- `gl.llm.complete(...)`, `gl.ai.prompt()`, `gl.complete(...)`, `gl.call_llm(...)`
- `gl.non_deterministic_block(...)`
- `self.ask_llm(...)`, `ask_genlayer(...)`
- standalone `@gl.contract`, `@gl.llm_call`

Verify before rejecting if a pattern might be an older SDK form. Reject fabricated SDK usage when it is clearly not real GenLayer code.

## Known Ecosystem Packages

These are real ecosystem packages or tools:

- `genlayer` npm CLI
- `genvm-linter` pip package
- `genlayer-test`, `genlayer-test[sim]`
- `genlayer-js`
- `genlayer-py`
- GenLayer VS Code extension
