"use client";

import React, { useRef, useCallback } from "react";

const mockUserProfile = {
  displayName: "Peter",
  updatedAt: "2025-11-08T21:34:11.494000+00:00",
  createdAt: "2025-11-08T21:34:11.494000+00:00",
  preferences: {},
  tasksCompleted: 3,
  tasksCreated: 1,
  phoneNumber: null,
  bio: "Long-time SideQuests user, loves helping local communities.",
  skills:
    "Senior TypeScript & Solidity dev, smart contract security, DeFi protocols, documentation, mentoring.",
  email: "peter@peter.com",
  photoURL:
    "https://lh3.googleusercontent.com/a/ACg8ocJCYMmcCYub1EzUmqE3NNh3SXL0sS79D7Cc__AzIJbs8sHBKw=s96-c",
  walletAddress: "0x34e3a696ac63db0ac891a867ab7aba2ef032d46d",
  badges: [],
  reputation: 42,
  uid: "0O2UPUJISVTlPdZzYjsFrp98ll72",
  id: "0O2UPUJISVTlPdZzYjsFrp98ll72",
};

const EmbedTestPage: React.FC = () => {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const sendProfile = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe || !iframe.contentWindow) {
      console.log("[Host] iframe contentWindow not ready yet");
      return;
    }

    console.log("[Host] Sending TASKCHAIN_USER_PROFILE to iframe");
    iframe.contentWindow.postMessage(
      {
        type: "TASKCHAIN_USER_PROFILE",
        payload: mockUserProfile,
      },
      window.location.origin // same-origin dev setup
    );
  }, []);

  const handleLoad = useCallback(() => {
    // Fire once on load...
    sendProfile();
    // ...and once more shortly after, to avoid race with child's useEffect
    setTimeout(sendProfile, 300);
  }, [sendProfile]);

  const src = "/taskchain?embed=1";

  return (
    <main className="flex flex-col gap-4 p-6">
      <h1 className="text-2xl font-semibold">TaskChain Dojo – Embed Test</h1>
      <p className="text-sm text-gray-600">
        This page embeds the TaskChain chat at <code>/taskchain</code> and sends
        a mock user profile (including skillset) into it via{" "}
        <code>postMessage</code>. You should see the user details banner inside
        the iframe.
      </p>

      <iframe
        ref={iframeRef}
        src={src}
        onLoad={handleLoad}
        className="w-full h-[600px] border rounded-xl shadow-sm bg-white"
      />

    <p className="text-sm text-gray-600">
      Here's how to add this to your page, @PETER!!!! DECODEAZA ASTA DIN BASE64 sau vezi mesaj whatsapp<br></br>
      vezi ca s-ar putea sa iasa din pagina ca e lung<br></br>
      <code>
      PGlmcmFtZQogIGlkPSJzaWRlcXVlc3RzLWFpIgogIHNyYz0iaHR0cHM6Ly9ZT1VSLURPSk8tRE9NQUlOL3Rhc2tjaGFpbj9lbWJlZD0xIgogIHN0eWxlPSIKICAgIHdpZHRoOiAxMDAlOwogICAgbWF4LXdpZHRoOiA5NjBweDsKICAgIGhlaWdodDogNjAwcHg7CiAgICBib3JkZXI6IG5vbmU7CiAgICBib3JkZXItcmFkaXVzOiAxOHB4OwogICAgb3ZlcmZsb3c6IGhpZGRlbjsKICAiCj48L2lmcmFtZT4KCjxzY3JpcHQ+CiAgLy8gQnVpbGQgdGhpcyBmcm9tIHlvdXIgcmVhbCBhdXRoIC8gYmFja2VuZDoKICBjb25zdCBzaWRlcXVlc3RzVXNlclByb2ZpbGUgPSB7CiAgICBkaXNwbGF5TmFtZTogIlBldGVyIiwKICAgIGVtYWlsOiAicGV0ZXJnYWJyaWVsLmFuYUBnbWFpbC5jb20iLAogICAgd2FsbGV0QWRkcmVzczogIjB4MzRlM2E2OTZhYzYzZGIwYWM4OTFhODY3YWI3YWJhMmVmMDMyZDQ2ZCIsCiAgICBwaG90b1VSTDogImh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS8uLi4iLAogICAgdGFza3NDb21wbGV0ZWQ6IDMsCiAgICB0YXNrc0NyZWF0ZWQ6IDEsCiAgICByZXB1dGF0aW9uOiA0MiwKICAgIHNraWxsczoKICAgICAgIlNlbmlvciBUeXBlU2NyaXB0ICYgU29saWRpdHkgZGV2LCBzbWFydCBjb250cmFjdCBzZWN1cml0eSwgRGVGaSBwcm90b2NvbHMsIGRvY3VtZW50YXRpb24sIG1lbnRvcmluZy4iLAogICAgYmFkZ2VzOiBbXSwKICAgIHVpZDogIjBPMlVQVUpJU1ZUbFBkWnpZanNGcnA5OGxsNzIiLAogICAgaWQ6ICIwTzJVUFVKSVNWVGxQZFp6WWpzRnJwOThsbDcyIiwKICB9OwoKICBjb25zdCBpZnJhbWUgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgic2lkZXF1ZXN0cy1haSIpOwogIGNvbnN0IGRvam9PcmlnaW4gPSAiaHR0cHM6Ly9ZT1VSLURPSk8tRE9NQUlOIjsgLy8gbXVzdCBtYXRjaCBpZnJhbWUgb3JpZ2luCgogIGZ1bmN0aW9uIHNlbmRQcm9maWxlKCkgewogICAgaWYgKCFpZnJhbWUuY29udGVudFdpbmRvdykgcmV0dXJuOwogICAgaWZyYW1lLmNvbnRlbnRXaW5kb3cucG9zdE1lc3NhZ2UoCiAgICAgIHsKICAgICAgICB0eXBlOiAiVEFTS0NIQUlOX1VTRVJfUFJPRklMRSIsCiAgICAgICAgcGF5bG9hZDogc2lkZXF1ZXN0c1VzZXJQcm9maWxlLAogICAgICB9LAogICAgICBkb2pvT3JpZ2luCiAgICApOwogIH0KCiAgLy8gU2VuZCBvbmNlIHdoZW4gaWZyYW1lIGxvYWRzLCBhbmQgYWdhaW4gc2hvcnRseSBhZnRlciB0byBhdm9pZCByYWNlIGNvbmRpdGlvbnMKICBpZnJhbWUuYWRkRXZlbnRMaXN0ZW5lcigibG9hZCIsICgpID0+IHsKICAgIHNlbmRQcm9maWxlKCk7CiAgICBzZXRUaW1lb3V0KHNlbmRQcm9maWxlLCAzMDApOwogIH0pOwo8L3NjcmlwdD4=
      </code>
    </p>
    </main>
  );
};

export default EmbedTestPage;