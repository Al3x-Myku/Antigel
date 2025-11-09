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

// ---------- Banner for embedded + profile ----------

const UserContextBanner: React.FC<{ user: UserProfile | null }> = ({ user }) => {
  if (!user) return null;

  const skillsPreview =
    user.skills || user.skillset || user.bio || "(no skills string provided)";

  return (
    <div className="mb-3 px-4 py-3 rounded-xl border border-[#4A4750] bg-[#3A3740] shadow-sm text-xs flex flex-col gap-1">
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
          <span className="font-semibold text-[#FAFDF6]">
            Signed in as{" "}
            {user.displayName ||
              user.email ||
              user.walletAddress ||
              "Unknown user"}
          </span>
          <span className="text-[10px] text-[#B0ADB5]">
            Wallet: {user.walletAddress || "N/A"} · Completed:{" "}
            {user.tasksCompleted ?? 0} · Created:{" "}
            {user.tasksCreated ?? 0} · Rep: {user.reputation ?? 0}
          </span>
        </div>
      </div>
      <div className="mt-1 text-[#FAFDF6]">
        <span className="font-medium">Skillset:</span>{" "}
        <span>{skillsPreview}</span>
      </div>
    </div>
  );
};

// ---------- Main page ----------

const TaskchainAgenticChat: React.FC = () => {
  const searchParams = useSearchParams();
  const [user, setUser] = useState<UserProfile | null>(null);

  const isEmbedded = searchParams.get("embed") === "1";

  // 1) Dev/testing: ?user=<base64(json)>
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
      // ignore invalid
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // 2) Real embedding: receive profile via postMessage
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      // In production: check event.origin
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

  // Initial greeting text
  const initialLabel = useMemo(() => {
    if (user) {
      const name =
        user.displayName || user.email || user.walletAddress || "there";
      return `Hi ${name}, I'm SideQuests AI. Ask me anything about tasks tailored to your profile and skillset.`;
    }
    return "Hi, I'm SideQuests AI. Ask me anything about SideQuests tasks and how to get involved.";
  }, [user]);

  // Suggestions, including "Share my account details" when we have a profile
  const suggestions = useMemo(() => {
    const base = [
      {
        title: "Show open tasks",
        message: "Show me only open / available tasks.",
      },
      {
        title: "Show completed tasks",
        message: "Show me only completed / verified tasks.",
      },
    ];

    if (user) {
      const profilePayload = {
        displayName: user.displayName,
        email: user.email,
        walletAddress: user.walletAddress,
        uid: user.uid || user.id,
        tasksCompleted: user.tasksCompleted ?? 0,
        tasksCreated: user.tasksCreated ?? 0,
        reputation: user.reputation ?? 0,
        badges: user.badges ?? [],
        skills:
          user.skills || user.skillset || user.bio || "No explicit skills.",
      };

      // This sends a special message the backend is instructed to parse.
      base.unshift({
        title: "Share my account details",
        message: `Here are my profile details (PROFILE_JSON): ${JSON.stringify(profilePayload)}`,
      });

      base.unshift({
        title: "Find tasks for my skills",
        message:
          `Use my shared profile (via PROFILE_JSON) and suggest a few tasks that match my skills. ${JSON.stringify(profilePayload)}`,
      });
    } else {
      base.unshift({
        title: "Help me get started",
        message:
          "Explain how SideQuests works and how I can find or create tasks.",
      });
    }

    return base;
  }, [user]);

  // Layout: embed vs direct
  const containerClass = isEmbedded
    ? "h-screen w-screen flex flex-col p-3 gap-2 bg-[#2D2A32]"
    : "min-h-screen w-full flex justify-center bg-[#2D2A32] p-6";

  const chatWrapperClass = isEmbedded
    ? "flex-1 min-h-0"
    : "w-full max-w-4xl h-[80vh] rounded-2xl border border-[#4A4750] bg-[#3A3740] shadow-sm overflow-hidden";

  // Key to reset per identity (optional but nice)
  const copilotKey = useMemo(() => {
    if (!user) return "sq-chat-anon";
    return (
      "sq-chat-user-" +
      (user.uid ||
        user.id ||
        user.walletAddress ||
        user.email ||
        "unknown")
    );
  }, [user]);

  return (
    <div className={containerClass}>
      {isEmbedded && user && <UserContextBanner user={user} />}

      <div className={chatWrapperClass}>
        <CopilotChat
          key={copilotKey}
          className="h-full w-full copilotKitChat"
          labels={{ initial: initialLabel }}
          suggestions={suggestions}
          RenderActionExecutionMessage={ToolCallMessage}
          RenderResultMessage={ToolResultMessage}
        />
      </div>
    </div>
  );
};

export default TaskchainAgenticChat;