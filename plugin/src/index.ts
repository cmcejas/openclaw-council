import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

/** JSON Schema for tool parameters (no @sinclair/typebox — OpenClaw loads this file without plugin node_modules). */
const councilRunParameters = {
  type: "object",
  additionalProperties: false,
  properties: {
    topic: {
      type: "string",
      description: "Question or decision to deliberate.",
    },
    mode: {
      type: "string",
      enum: ["standard", "live", "research"],
    },
    rounds: {
      type: "integer",
      minimum: 1,
      maximum: 8,
      description: "Subagent turns (sequential).",
    },
  },
  required: ["topic", "mode"],
} as const;

type CouncilRunParams = {
  topic: string;
  mode: "standard" | "live" | "research";
  rounds?: number;
};

function extractAssistantText(messages: unknown): string {
  if (!Array.isArray(messages)) {
    return "";
  }
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i] as Record<string, unknown>;
    if (m.role !== "assistant") {
      continue;
    }
    const content = m.content;
    if (typeof content === "string") {
      return content;
    }
    if (Array.isArray(content)) {
      const parts: string[] = [];
      for (const part of content) {
        if (part && typeof part === "object" && "text" in part) {
          const t = (part as { text?: unknown }).text;
          if (typeof t === "string" && t.length > 0) {
            parts.push(t);
          }
        }
      }
      if (parts.length > 0) {
        return parts.join("\n");
      }
    }
  }
  return "";
}

function outputTextFromWaitResult(result: unknown): string {
  if (!result || typeof result !== "object") {
    return "";
  }
  const r = result as Record<string, unknown>;
  if (typeof r.outputText === "string") {
    return r.outputText;
  }
  const completed = r.completed;
  if (completed && typeof completed === "object") {
    const c = completed as Record<string, unknown>;
    if (typeof c.outputText === "string") {
      return c.outputText;
    }
  }
  return "";
}

export default definePluginEntry({
  id: "openclaw-council",
  name: "OpenClaw Council",
  description: "Council deliberation tool (council_run) for multi-role prompts via subagents.",
  register(api) {
    api.registerTool(
      {
        name: "council_run",
        description:
          "Run a short council-style deliberation for a topic using a background subagent turn. " +
          "Returns assistant text from the subagent session (MVP; persist transcript via CLI separately).",
        parameters: councilRunParameters,
        async execute(_toolCallId, params: CouncilRunParams) {
          const sub = api.runtime.subagent;
          const timeoutMs = api.runtime.agent.resolveAgentTimeoutMs(api.config);
          const rounds = params.rounds ?? 1;
          const sessionKey = `agent:main:subagent:council-${crypto.randomUUID()}`;
          const segments: string[] = [];

          try {
            for (let r = 1; r <= rounds; r++) {
              const roleHint =
                params.mode === "research"
                  ? "Act as Researcher: gather concise considerations, then implications."
                  : params.mode === "live"
                    ? "Act in a brief brainstorm style."
                    : "Act in a formal council round (one focused contribution).";

              const message = [
                `Council mode: ${params.mode} (turn ${r}/${rounds}).`,
                roleHint,
                "",
                `Topic: ${params.topic}`,
                "",
                "Reply with a single clear contribution. No tool calls required unless essential.",
              ].join("\n");

              const { runId } = await sub.run({
                sessionKey,
                message,
                deliver: false,
              });

              const waitResult = await sub.waitForRun({ runId, timeoutMs });
              const fromWait = outputTextFromWaitResult(waitResult);
              const { messages } = await sub.getSessionMessages({
                sessionKey,
                limit: 50,
              });
              const fromMessages = extractAssistantText(messages);
              const text = (fromMessages || fromWait).trim();

              if (!text) {
                segments.push(`[turn ${r}] (no assistant text; check subagent policy and logs)`);
              } else {
                segments.push(`### Turn ${r}\n\n${text}`);
              }
            }

            const body = segments.join("\n\n---\n\n");
            return {
              content: [{ type: "text", text: body }],
            };
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            api.logger.error(`council_run failed: ${msg}`);
            return {
              content: [
                {
                  type: "text",
                  text: `council_run error: ${msg}`,
                },
              ],
            };
          } finally {
            try {
              await sub.deleteSession({ sessionKey });
            } catch {
              /* best-effort cleanup */
            }
          }
        },
      },
    );
  },
});
