# PowerMem Plugin for Claude Code

The full Claude Code integration guide — the auto-setup prompt, manual steps, the
two connection modes (HTTP / MCP), hooks, configuration, troubleshooting, and
uninstall — now lives in the docs and is the single source of truth:

**➡ [docs/integrations/claude_code.md](../../docs/integrations/claude_code.md)**

This directory still contains the plugin itself (`.claude-plugin/`, `hooks/`,
`skills/`, `config/`, `.mcp.json`). To load it:

```bash
claude --plugin-dir /path/to/powermem/apps/claude-code-plugin
```
