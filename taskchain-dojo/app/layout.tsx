import type { Metadata } from "next";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";
import React from "react";
import { CopilotKit } from "@copilotkit/react-core";

export const metadata: Metadata = {
  title: "TaskChain Dojo",
  description: "Taskchain matchmaking copilot UI (AG-UI + CopilotKit)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="agentic_chat" // must match key in runtime.agents
          showDevConsole={false}
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}