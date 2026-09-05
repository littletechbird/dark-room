# Agent flow example: agent sees only the handle

This walkthrough shows how an agent-watched desktop keeps plaintext out of
model context. The agent may observe commands, screenshots, and tool output —
but never the secret body.

## Setup (human / local process only)

```bash
# From repo root, with venv active
export DARKROOM_VAULT=/tmp/darkroom-demo
mkdir -p "$DARKROOM_VAULT"

# Secret comes from TTY/stdin — NOT argv (argv is visible to agents/process lists)
printf 'my-real-api-key-do-not-log' | python -m darkroom.cli \
  --vault-dir "$DARKROOM_VAULT" \
  mint --label github-pat --origin https://api.github.com
```

Example stdout (agent-visible):

```
dr_sec_AbCdEfGhIjKlMnOpQrStUv
```

The agent is told only: "credential handle is `dr_sec_AbCdEfGhIjKlMnOpQrStUv`".

## What the agent may do

```bash
python -m darkroom.cli --vault-dir "$DARKROOM_VAULT" list
```

Output (metadata only):

```
dr_sec_AbCdEfGhIjKlMnOpQrStUv	github-pat	active	origins=https://api.github.com
```

```bash
python -m darkroom.cli --vault-dir "$DARKROOM_VAULT" fill-sim \
  --handle dr_sec_AbCdEfGhIjKlMnOpQrStUv \
  --field Authorization \
  --form-file /tmp/fake_egress_form.txt \
  --origin https://api.github.com
```

Agent-visible stdout:

```
filled field='Authorization' handle=dr_sec_AbCdEfGhIjKlMnOpQrStUv value=****
form_file=/tmp/fake_egress_form.txt
```

The form file on disk holds the resolved value for a local egress helper.
That file must not be read back into the agent transcript.

## What the agent must never do

- Ask for the secret in chat or tools
- `cat` the form file into the conversation
- Pass the secret on argv (`mint --secret ...` is intentionally unsupported)
- Reuse a handle against a non-allowlisted origin

## Revoke when done

```bash
python -m darkroom.cli --vault-dir "$DARKROOM_VAULT" revoke \
  --handle dr_sec_AbCdEfGhIjKlMnOpQrStUv
```

After revoke, `fill-sim` / `resolve` fail; `list` still shows metadata only
(no plaintext).
