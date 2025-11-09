"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import "@copilotkit/react-ui/styles.css";
import "./style.css";
import { CopilotChat } from "@copilotkit/react-ui";

type UserProfile = {
  displayName?: string;
  email?: string;
  walletAddress?: string;
  photoURL?: string;
  uid?: string;
  id?: string;
  tasksCompleted?: number;
  tasksCreated?: number;
  reputation?: number;
  badges?: any[];
  skills?: string;
  skillset?: string;
  bio?: string;
  [key: string]: any;
};

// ---------- Tool UI helpers ----------

const getToolName = (message: any): string => {
  const raw =
    message?.actionExecution?.name ||
    message?.tool?.name ||
    message?.name ||
    message?.metadata?.toolName ||
    message?.metadata?.name ||
    message?.toolName ||
    "";

  if (!raw) return "Tool";

  return raw
    .replace(/^tool:/i, "")
    .replace(/^action:/i, "")
    .replace(/^mcp[_-]/i, "")
    .replace(/_/g, " ")
    .trim();
};

const ToolCallMessage = ({ message }: any) => {
  const toolName = getToolName(message);

  return (
    <div className="tc-tool-pill-wrapper">
      <div className="tc-tool-pill">
        <span className="tc-tool-icon">🛠</span>
        <span className="tc-tool-label">
          Running <strong>{toolName}</strong>...
        </span>
      </div>
    </div>
  );
};

const ToolResultMessage = ({ message, children }: any) => {
  const toolName = getToolName(message);

  return (
    <div className="tc-tool-message">
      <div className="tc-tool-header">
        <span className="tc-tool-chip">
          <span className="tc-tool-icon">⚙️</span>
          <span className="tc-tool-chip-text">{toolName}</span>
        </span>
        <span className="tc-tool-sub">Result</span>
      </div>
      <div className="tc-tool-body">{children}</div>
    </div>
  );
};

// ---------- System prompt ----------

function buildSystemPrompt(user: UserProfile | null): string {
  const base = `
You are the SideQuests / TaskChain AI assistant.

You run inside a Task Dojo UI that is connected to:
- The TaskChain MCP tools on Sepolia for live on-chain task data.
- A host app that may provide an authenticated user profile.

Rules:
- Always use the TaskChain MCP tools (list_tasks, get_task, list_active_tasks, etc.) for real data.
- Never invent on-chain state.
- When a user profile is provided, personalize using that profile & skillset.
- DO NOT HALLUCINATE!!!
- DO NOT FABRICATE TASKS!!
If the user asks for tasks and you don't receive anything, don't hallucinate, fabricate, or lie to the user.
Reward should be shown in raw format only, for example: for 1e-16, you need to show 100.
`.trim();

  if (!user) {
    return `${base}

User profile:
- Not provided.

Behavior:
- Provide helpful, general guidance about available tasks and how the platform works.
- If the user mentions their skills or wallet, adapt based on that conversation.
- DO NOT HALLUCINATE!!!
- DO NOT FABRICATE TASKS!!
`;
  }

  const skillsText =
    user.skills ||
    user.skillset ||
    user.bio ||
    "No explicit skills string provided.";

  const badgesCount = Array.isArray(user.badges) ? user.badges.length : 0;

  return `${base}

User Profile (trusted, provided by the host application):
- Display Name: ${user.displayName || "N/A"}
- Email: ${user.email || "N/A"}
- Wallet Address: ${user.walletAddress || "N/A"}
- UID / ID: ${user.uid || user.id || "N/A"}
- Tasks Completed: ${user.tasksCompleted ?? 0}
- Tasks Created: ${user.tasksCreated ?? 0}
- Reputation: ${user.reputation ?? 0}
- Badges: ${badgesCount} badge(s)
- Skillset: ${skillsText}

Instructions:
- Treat this profile as the identity of the current user.
- Use their skillset, experience, and reputation to:
  - Suggest tasks that fit their level and interests.
  - Highlight opportunities relevant to their wallet / history when appropriate.
- Do NOT claim to perform on-chain actions or see private balances.
- Stay grounded in data from TaskChain tools.
- DO NOT HALLUCINATE!!!
`;
}

// ---------- Signed-in banner (embed only) ----------

const UserContextBanner: React.FC<{ user: UserProfile | null }> = ({ user }) => {
  if (!user) return null;

  const skillsPreview =
    user.skills || user.skillset || user.bio || "(no skills string provided)";

  return (
    <div className="mb-3 px-4 py-3 rounded-xl border bg-white/90 shadow-sm text-xs flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {user.photoURL && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.photoURL}
            alt={user.displayName || "User avatar"}
            className="w-7 h-7 rounded-full object-cover"
          />
        )}
        <div className="flex flex-col">
          <span className="font-semibold text-gray-900">
            Signed in as{" "}
            {user.displayName ||
              user.email ||
              user.walletAddress ||
              "Unknown user"}
          </span>
          <span className="text-[10px] text-gray-500">
            Wallet: {user.walletAddress || "N/A"} · Completed:{" "}
            {user.tasksCompleted ?? 0} · Created:{" "}
            {user.tasksCreated ?? 0} · Rep: {user.reputation ?? 0}
          </span>
        </div>
      </div>
      <div className="mt-1 text-gray-700">
        <span className="font-medium">Skillset:</span>{" "}
        <span>{skillsPreview}</span>
      </div>
    </div>
  );
};

// ---------- Main component ----------

const TaskchainAgenticChat: React.FC = () => {
  const searchParams = useSearchParams();
  const [user, setUser] = useState<UserProfile | null>(null);

  const isEmbedded = searchParams.get("embed") === "1";

  // 1) Optional: ?user=<base64(json)>
  useEffect(() => {
    const encoded = searchParams.get("user");
    if (!encoded) return;

    try {
      const json = atob(encoded);
      const parsed = JSON.parse(json);
      if (parsed && typeof parsed === "object") {
        setUser((prev) => ({ ...(prev || {}), ...parsed }));
      }
    } catch {
      // ignore malformed
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // 2) Primary: postMessage from host
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      // In production: restrict to trusted origins
      // if (event.origin !== "https://your-host.app") return;

      if (event.data?.type === "TASKCHAIN_USER_PROFILE") {
        const profile = event.data.payload;
        if (profile && typeof profile === "object") {
          setUser(profile as UserProfile);
        }
      }
    };

    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  const systemPrompt = useMemo(() => buildSystemPrompt(user), [user]);

  const initialLabel = useMemo(() => {
    if (user) {
      const name =
        user.displayName || user.email || user.walletAddress || "there";
      return `Hi ${name}, I'm SideQuests AI. Ask me anything about tasks tailored to your profile and skillset.`;
    }
    return "Hi, I'm SideQuests AI. Ask me anything about SideQuests tasks and how to get involved.";
  }, [user]);

  // Layout differs for embed vs direct access
  const containerClass = isEmbedded
    ? "h-screen w-screen flex flex-col p-3 gap-2 bg-slate-50"
    : "min-h-screen w-full flex justify-center bg-slate-50 p-6";

  const chatWrapperClass = isEmbedded
    ? "flex-1 min-h-0"
    : "w-full max-w-4xl h-[80vh] rounded-2xl border bg-white shadow-sm overflow-hidden";

  return (
    <div className={containerClass}>
      {isEmbedded && user && <UserContextBanner user={user} />}

      <div className={chatWrapperClass}>
        <CopilotChat
          className="h-full w-full copilotKitChat"
          instructions={systemPrompt}
          labels={{ initial: initialLabel }}
          suggestions={[
            {
              title: "Find tasks for my skills",
              message:
                "Based on my profile and skillset, suggest a few tasks that fit me.",
            },
            {
              title: "Show open tasks",
              message: "Show me only open / available tasks.",
            },
            {
              title: "Show completed tasks",
              message: "Show me only completed / verified tasks.",
            },
          ]}
          RenderActionExecutionMessage={ToolCallMessage}
          RenderResultMessage={ToolResultMessage}
        />
      </div>
    </div>
  );
};

export default TaskchainAgenticChat;