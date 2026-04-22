# OpenClaw plugin tools and empty tool catalogs

This note explains why the **openclaw-council** native plugin can show as loaded while the agent still sees **no** `council_run`, and how to fix it.

## Primary fix: use `tools.alsoAllow` with `profile: "coding"`

If you use **`tools.profile: "coding"`**, OpenClaw’s policy pipeline can **drop plugin-registered tools** after they are built (they appear in plugin inspect / `createOpenClawTools`, then disappear **post-policy**). Community traces match this: plugin tools present pre-policy, **gone** post-policy, with `coding` profile.

**Fix:** add plugin tool names **additively** with **`tools.alsoAllow`**, not only `tools.allow`.

1. Remove any restrictive `tools.allow` if you were experimenting (or ensure you are not combining conflicting modes — see OpenClaw docs for whether `allow` and `alsoAllow` can coexist in your version).

2. Set something equivalent to:

```json5
{
  tools: {
    profile: "coding",
    alsoAllow: ["council_run"],
  },
}
```

3. Restart the gateway, then verify `systemPromptReport.tools.entries` includes **`council_run`**.

**CLI example:**

```bash
openclaw config unset tools.allow
openclaw config set tools.alsoAllow '["council_run"]'
openclaw gateway restart
```

Adjust the `set` command to match your OpenClaw CLI if the key path differs.

**References:** [openclaw/openclaw#47683](https://github.com/openclaw/openclaw/issues/47683) (discussion and `alsoAllow` workaround in comments), [openclaw/openclaw#50328](https://github.com/openclaw/openclaw/issues/50328) (plugin tools vs agent list).

## Symptoms

- `openclaw plugins inspect openclaw-council` shows the plugin loaded and lists `council_run`.
- `openclaw agent --json --agent main ...` metadata has **no** `council_run` in `systemPromptReport.tools.entries`.

Inspection reflects registration; the **agent turn** applies **tool policy** after tool resolution.

## `tools.allow` is exclusive (different from `alsoAllow`)

A **non-empty** `tools.allow` means: *only* what is listed (after group expansion) remains; everything else is blocked.

Examples that bite:

- `allow: ["openclaw-council"]` only → often **zero** tools (plugin id may not expand the way you expect, and you excluded all builtins).
- `allow: ["group:openclaw", "council_run"]` → builtins from the group may appear, but **`council_run` can still be missing** if the **profile** strips plugin tools **unless** they are carried by **`alsoAllow`** (see §Primary fix).

For **additive** “keep coding defaults + enable plugin tools”, prefer **`alsoAllow`**.

## Manifest `id`

This repo uses plugin id **`openclaw-council`** in `openclaw.plugin.json` and `definePluginEntry`. The callable tool name is **`council_run`**.

## Per-agent overrides

`agents.list[].tools.*` can further restrict tools. Check the **main** agent entry for `tools.profile`, `tools.allow`, `tools.alsoAllow`, and `tools.deny`.

## CLI vs gateway / `--local`

`openclaw agent` can run via the gateway or embedded. See [`openclaw agent` CLI](https://docs.openclaw.ai/cli/agent). Compare with `--local` if connect/timeouts confuse results.

## Inspect effective policy

```bash
openclaw sandbox explain --agent main --json
```

## Plugin loads from source: no extra `npm install` required

This repo’s `plugin/src/index.ts` uses **inline JSON Schema** for `parameters` so OpenClaw does not need `@sinclair/typebox` (or any `plugin/node_modules`) when loading the linked `.ts` entry. If you fork the plugin and add npm dependencies, run `npm install` inside `plugin/` so the gateway can resolve them.

## After `council_run` appears: runtime failures

If the tool is listed but calls fail, check subagent policy (`tools.subagents`), sandbox settings, and gateway logs.

## References

- [Tools and Plugins](https://docs.openclaw.ai/tools) — profiles, groups.
- [Sandbox vs Tool Policy](https://docs.openclaw.ai/gateway/sandbox-vs-tool-policy-vs-elevated).
- [Building Plugins / Agent tools](https://docs.openclaw.ai/plugins/agent-tools).
- [Plugin Runtime Helpers](https://docs.openclaw.ai/plugins/sdk-runtime) — `api.runtime.subagent`.
