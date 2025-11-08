import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  ExperimentalEmptyAdapter,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

const TASKCHAIN_AGUI_URL =
  process.env.TASKCHAIN_AGUI_URL || "http://localhost:7777/agui";

const runtimeInstance = new CopilotRuntime({
  agents: {
    agentic_chat: new HttpAgent({
      url: TASKCHAIN_AGUI_URL,
    }),
  },
});

const serviceAdapter = new ExperimentalEmptyAdapter();

export async function POST(req: NextRequest) {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime: runtimeInstance,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
}

export const GET = POST;