# OpenClaw plugin tools and empty tool catalogs

This note explains why the **openclaw-council** native plugin can show as loaded while the agent still sees **no tools** (or no `council_run`), and how to fix it. It aligns with current OpenClaw documentation on tool policy and plugin registration.

## Symptoms

- `openclaw plugins inspect openclaw-council` shows the plugin loaded and lists `council_run`.
- `openclaw agent --json --agent main ...` metadata reports an empty tool list, or the model says `council_run` is unavailable.

Those can both be true: inspection reflects registration; the **agent turn** applies **tool policy** on top.

## 1. Non-empty `tools.allow` is exclusive

OpenClaw’s tool policy treats a **non-empty** `tools.allow` as: *only* what is listed (after group expansion) remains; everything else is blocked.

So a config like:

```json5
{
  tools: { allow: ["group:openclaw"] },
}
```

includes **built-in** tools only. The `group:openclaw` group **explicitly excludes plugin tools**. Plugin tools will **not** appear unless you also allow them.

**Fix:** Add either the **plugin manifest id** or the **tool name** (see §3). For example:

```json5
{
  tools: {
    allow: ["group:openclaw", "openclaw-council"],
  },
}
```

or:

```json5
{
  tools: {
    allow: ["group:openclaw", "council_run"],
  },
}
```

(`deny` still wins over `allow` if both apply.)

## 2. Optional plugin tools need an allowlist entry

In this repo, `council_run` is registered with `{ optional: true }` so operators can opt in explicitly (recommended for tools with side effects such as subagent runs).

Per OpenClaw’s plugin docs, optional tools must be enabled via `tools.allow` using either:

- the **tool name** (`council_run`), or
- the **plugin id** from `openclaw.plugin.json` / `definePluginEntry` (here: **`openclaw-council`**), which can enable all tools from that plugin.

If optional tools are not allowlisted, they are omitted from the model-facing catalog even when the plugin loads.

## 3. Manifest `id` must match what you allowlist

The plugin id in code and manifest must be consistent. This repo uses **`openclaw-council`** everywhere.

If your config uses a different string (for example the npm package name only), allowlisting may not match and the tool stays blocked.

## 4. Per-agent overrides

`agents.list[].tools.*` can further restrict tools. Check the **main** agent entry for:

- `tools.profile` (e.g. `minimal` is extremely small)
- `tools.allow` / `tools.deny`
- `tools.subagents.*` if subagent runs are restricted

Precedence is documented under [Multi-Agent Sandbox & Tools](https://docs.openclaw.ai/tools/multi-agent-sandbox-tools).

## 5. CLI vs gateway / `--local`

`openclaw agent` can run via the gateway or embedded. From the CLI docs:

- **`--local`** forces embedded execution after plugin registry preload.
- Without it, behavior depends on gateway connectivity and fallback.

If you suspect a path mismatch, compare:

```bash
openclaw agent --local --json --timeout 60000 --agent main --message "List tools you can call."
```

against the non-`--local` invocation.

## 6. Inspect effective policy

Use:

```bash
openclaw sandbox explain --agent main --json
```

Review effective allow/deny and sandbox tool policy for the agent you are testing.

## 7. After `council_run` appears: runtime failures

If the tool is listed but calls fail, check:

- Subagent permissions (`tools.subagents` / sandbox policy).
- Gateway logs for subagent or policy errors.
- Model override opt-in if the plugin ever passes custom `provider` / `model` to `subagent.run` (this repo does not, by default).

## References

- [Tools and Plugins](https://docs.openclaw.ai/tools) — profiles, groups, `group:openclaw` excludes plugins.
- [Sandbox vs Tool Policy](https://docs.openclaw.ai/gateway/sandbox-vs-tool-policy-vs-elevated) — “If `allow` is non-empty, everything else is treated as blocked.”
- [Building Plugins / Agent tools](https://docs.openclaw.ai/plugins/agent-tools) — optional tools and `tools.allow`.
- [Plugin Runtime Helpers](https://docs.openclaw.ai/plugins/sdk-runtime) — `api.runtime.subagent`.
- [`openclaw agent` CLI](https://docs.openclaw.ai/cli/agent) — `--local`, plugin preload.
