import { create } from "zustand";
import { useAuthStore } from "./authStore";

export const useChatStore = create((set, get) => ({
  turns: [],
  isStreaming: false,
  streamBuffer: "",

  addTurn: (turn) => set((s) => ({ turns: [...s.turns, turn] })),

  appendToken: (token) =>
    set((s) => ({ streamBuffer: s.streamBuffer + token })),

  flushStream: (turnType = "assistant") => {
    const { streamBuffer } = get();
    if (!streamBuffer) return;
    set((s) => ({
      turns: [...s.turns, { role: "assistant", content: streamBuffer, turn_type: turnType }],
      streamBuffer: "",
      isStreaming: false,
    }));
  },

  startStream: () => set({ isStreaming: true, streamBuffer: "" }),
  stopStream: () => set({ isStreaming: false }),

  sendMessage: async (sessionId, message) => {
    const { token } = useAuthStore.getState();
    set((s) => ({
      turns: [...s.turns, { role: "user", content: message }],
      isStreaming: true,
      streamBuffer: "",
    }));

    const response = await fetch(`/api/sessions/${sessionId}/message/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Token ${token}`,
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      set({ isStreaming: false });
      return;
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("event-stream")) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              set((s) => ({ streamBuffer: s.streamBuffer + data.token }));
            }
            if (data.done) {
              get().flushStream(data.off_topic ? "off_topic" : "free_text");
              if (data.paths && data.paths.length) {
                set((s) => ({
                  turns: [
                    ...s.turns,
                    { role: "paths", turn_type: "paths", round: data.round ?? 0, paths: data.paths },
                  ],
                }));
              }
            }
          } catch {}
        }
      }
    } else {
      const data = await response.json();
      set((s) => ({
        turns: [...s.turns, { role: "assistant", content: data.reply, turn_type: data.off_topic ? "off_topic" : "free_text" }],
        isStreaming: false,
        streamBuffer: "",
      }));
    }
  },

  loadFromSession: (sessionData) => {
    const turns = (sessionData.turns || []).map((t) => ({
      role: t.role,
      content: t.content,
      turn_type: t.turn_type,
    }));
    set({ turns });
  },

  clear: () => set({ turns: [], streamBuffer: "", isStreaming: false }),
}));
