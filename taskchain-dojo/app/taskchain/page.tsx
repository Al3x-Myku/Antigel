"use client";

import React from "react";
import "@copilotkit/react-ui/styles.css";
import "./style.css";
import { CopilotChat } from "@copilotkit/react-ui";

const TaskchainAgenticChat: React.FC = () => {
  return (
    <div className="h-screen w-screen">
      <CopilotChat
        className="h-full w-full copilotKitChat"
        labels={{
          initial:
            "Hi, I'm your TaskChain copilot. Tell me your skills & preferences and I'll fetch matching on-chain tasks from the protocol.",
        }}
        suggestions={[
          {
            title: "Match tasks for me",
            message:
              "I know Solidity and Rust, like infra and DeFi, dislike frontend. Suggest 3 matching on-chain tasks and explain why.",
          },
          {
            title: "Only open tasks",
            message:
              "Show me only open/available tasks that fit a junior Solidity dev.",
          },
        ]}
      />
    </div>
  );
};

export default TaskchainAgenticChat;