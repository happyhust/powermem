# PowerMem — automated Claude Code setup

This file is a **prompt for Claude Code**. Open Claude Code in your terminal and say:

> Read and follow `apps/claude-code-plugin/SETUP.md` to set up PowerMem memory for Claude Code.

Claude Code will then run the steps below: detect whether you are in the PowerMem
source tree or not, ask you for the few required secrets, and wire PowerMem up as a
**globally enabled** plugin so every `claude` session (interactive AND non-interactive
`claude -p`) uses it automatically — no per-session `--plugin-dir` flag.

---

Set up PowerMem memory for Claude Code on this machine **globally**. Do the whole
integration autonomously and ask me for any secret you need — never invent credentials.

This procedure is **idempotent**: it is safe to re-run. Each step must detect existing
state and either skip, reuse, or refresh it instead of failing or duplicating work.

1. DETECT CONTEXT. The current directory is the PowerMem source tree if a
   pyproject.toml here has name = "powermem" (or src/powermem/ and
   apps/claude-code-plugin/ both exist). Tell me which path you will take:
     - SOURCE  -> build & deploy from this checkout and install the Claude Code
                  plugin GLOBALLY in HTTP mode (hooks -> REST; needs Go 1.22+).
     - PIP     -> install from PyPI and connect via the powermem-mcp server
                  (the plugin is NOT on PyPI, so pip users integrate over MCP).

2. COLLECT CONFIG (idempotent). If a .env already exists in the working directory
   with LLM_PROVIDER / LLM_API_KEY / LLM_MODEL set, REUSE it and only ask me about
   anything missing. Otherwise ask for: LLM provider (anthropic / openai / qwen /
   ...), LLM API key, and LLM model. Use zero-config defaults for the rest
   (storage = embedded seekdb, embedder = local all-MiniLM-L6-v2) unless I say
   otherwise. Write/patch the .env (copy .env.example if present) filling
   LLM_PROVIDER / LLM_API_KEY / LLM_MODEL. For a custom endpoint, the var is the
   provider-prefixed *_LLM_BASE_URL (e.g. OPENAI_LLM_BASE_URL, QWEN_LLM_BASE_URL) —
   verify the exact spelling against .env.example.full; a typo is silently ignored.
   Never echo my key back in full.

3a. SOURCE path (global install):
    - pip install -e .   (no-op if already installed editable from this checkout)
    - Build the hook binaries FIRST — they get copied into Claude's plugin cache at
      install time, so they must exist on disk before step "install":
        if Go 1.22+ is present:  make build-claude-hook
        else tell me, and offer to install Go or fall back to the PIP path below.
    - Ensure the plugin's root .mcp.json stays empty ({}) — default HTTP mode.
    - STAGE the plugin into a stable, Claude-owned location so the marketplace does
      NOT depend on this checkout — you can move or delete the repo afterwards and
      memory keeps working. Copy the whole plugin dir (built binaries included) into
      ~/.claude/marketplaces/powermem:
        DEST="$HOME/.claude/marketplaces/powermem"
        mkdir -p "$DEST"
        rsync -a --delete "<ABS_PATH>/apps/claude-code-plugin/" "$DEST/"
          # no rsync? rm -rf "$DEST" && cp -a "<ABS_PATH>/apps/claude-code-plugin/." "$DEST/"
      The binaries from `make build-claude-hook` must already be on disk before this
      copy. Re-copy on every re-run so the staged dir tracks your latest build.
    - Register the marketplace from the STAGED dir (it ships
      .claude-plugin/marketplace.json) — never from the repo:
        claude plugin marketplace add "$DEST"
      If it reports "already on disk", refresh it instead:
        claude plugin marketplace update powermem
    - Install + enable the plugin globally (user scope). Install auto-enables it:
        claude plugin install memory-powermem@powermem --scope user
      IMPORTANT idempotency rule: a plain re-install is a no-op and does NOT refresh
      the cached copy. If the plugin is already installed AND you just rebuilt the
      binaries or changed the plugin, force a refresh:
        claude plugin uninstall memory-powermem@powermem
        claude plugin install   memory-powermem@powermem --scope user
      (Enablement is preserved across uninstall+reinstall.)
    - Start the API server only if it is not already healthy (idempotent):
        curl -s http://localhost:8848/api/v1/system/health   # if not healthy:
        powermem-server --host 0.0.0.0 --port 8848           # run in background
    - Confirm the plugin is enabled:  claude plugin list  (look for
      memory-powermem@powermem). Do NOT print a --plugin-dir command — it is global
      now; every `claude` and `claude -p` loads it automatically.

3b. PIP path:
    - Ensure uvx is available (offer to install uv if missing), then:
      pip install powermem
    - Register the MCP server globally so it persists across sessions (stdio = no
      port), run from the directory holding the .env. Idempotent: if `claude mcp get
      powermem` already exists, remove it first, then add:
        claude mcp remove powermem 2>/dev/null; claude mcp add powermem -- uvx powermem-mcp stdio

4. VERIFY with a real round-trip — do not claim success without data. Run the exact
   commands below and substitute nothing except the noted placeholder. Do NOT mark
   this step done until you have seen a non-empty search result actually come back.

   SOURCE/HTTP path — run a/b/c/d/e in order:

   a. Confirm the server answers (output must contain "status":"healthy"):
        curl -s -m 5 http://localhost:8848/api/v1/system/health

   b. WRITE a probe memory. CRITICAL SCHEMA: the request body is a single "content"
      STRING field — NOT a mem0-style "messages" array. Sending {"messages":[...]}
      returns HTTP 422 `{"detail":[{"type":"missing","loc":["body","content"]...}]}`.
      Use a unique user_id so the probe is isolated from real data:
        curl -s -m 60 -X POST http://localhost:8848/api/v1/memories \
          -H 'Content-Type: application/json' \
          -d '{"content":"PowerMem setup probe: my favorite test fruit is dragonfruit-zx9.","user_id":"powermem_setup_probe"}'
      Expected: JSON with "success": true and a data[0].memory_id (a long numeric
      string). The call can take 10-30s because the LLM extracts facts — KEEP the
      -m 60 timeout and WAIT; do not background it or abort early. Save the returned
      data[0].memory_id (a.k.a. data[0].id) — you need it for cleanup in (e).

   c. SEARCH it back. CRITICAL SCHEMA: the body field is "query" (not "question" or
      "text"), with the SAME user_id you wrote with:
        curl -s -m 30 -X POST http://localhost:8848/api/v1/memories/search \
          -H 'Content-Type: application/json' \
          -d '{"query":"what is my favorite test fruit","user_id":"powermem_setup_probe","limit":5}'
      Expected: data.total >= 1 and data.results[0].content mentions dragonfruit-zx9.
      If data.total is 0 the round-trip FAILED — do NOT report success. Re-check the
      server log and the embedder, retry the write in (b) once, then escalate to me.

   d. SHOW me both the write JSON and the search JSON (this is the proof of success).

   e. CLEAN UP the probe — delete by the id from (b), then confirm it is gone:
        curl -s -m 10 -X DELETE http://localhost:8848/api/v1/memories/<MEMORY_ID>
      Re-run the search from (c): data.total must now be 0.

   f. BONUS (proves global + headless wiring; do it if you can). Start the server with
      its output redirected to a log so you can grep it (if you have not already):
        powermem-server --host 0.0.0.0 --port 8848 > /tmp/powermem-server.log 2>&1 &
      Note the current log length, run a headless prompt from an UNRELATED dir with NO
      --plugin-dir, then show the two new hook-driven calls it triggers:
        ( cd /tmp && claude -p "Reply with exactly: probe ok" )
      Then in /tmp/powermem-server.log, AFTER that run, you MUST see both:
        POST /api/v1/memories/search   <- UserPromptSubmit hook (auto-recall)
        POST /api/v1/memories          <- SessionEnd hook (auto-save)
      Seeing both proves PowerMem loads automatically in every `claude`/`claude -p`.

   PIP/MCP path: confirm `claude mcp list` shows powermem as "connected" (not
   "failed"). If it shows failed, run `claude mcp get powermem` and verify the
   configured command resolves on PATH.

5. SUMMARIZE: path taken, where .env lives, where the staged marketplace lives
   (~/.claude/marketplaces/powermem — independent of this repo), the server URL,
   how memory is wired
   (HTTP hooks vs MCP tools — recall is auto-injected on UserPromptSubmit, not a
   tool the model calls; writes happen on SessionEnd/PostCompact), confirmation that
   it is enabled globally, and the fact that I just run `claude` (or `claude -p`)
   with nothing extra. Note: the background server does not survive a reboot — offer
   to set up a systemd user service for autostart.

## Re-running / refreshing later

This file is safe to re-run end to end. The only manual-feeling case is refreshing
the cached plugin after you change the plugin or rebuild the Go hooks at the SAME
version: rebuild (`make build-claude-hook`), re-copy the result into the staged
marketplace (`rsync -a --delete <ABS_PATH>/apps/claude-code-plugin/ ~/.claude/marketplaces/powermem/`),
then force-refresh the cache with `claude plugin uninstall memory-powermem@powermem`
followed by `claude plugin install memory-powermem@powermem --scope user` (or bump the
version in .claude-plugin/plugin.json so `claude plugin update memory-powermem` picks it up).

To turn it off without uninstalling: `claude plugin disable memory-powermem@powermem`
(re-enable with `claude plugin enable ...`). To disable only prompt-time search
injection, set POWERMEM_PROMPT_SEARCH=0. The hook talks to POWERMEM_BASE_URL
(default http://localhost:8848).

For the full manual reference, see ../../docs/integrations/claude_code.md
