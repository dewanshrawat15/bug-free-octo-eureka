import { create } from "zustand";
import { useAuthStore } from "./authStore";

export const useMetricsStore = create((set, get) => ({
  events: [],
  sessionId: null,

  setSessionId: (id) => set({ sessionId: id }),

  track: (eventType, payload = {}) => {
    const { sessionId } = get();
    const event = {
      event_type: eventType,
      payload,
      ...(sessionId ? { session_id: sessionId } : {}),
    };
    set((s) => ({ events: [...s.events, event] }));
    if (get().events.length >= 5) {
      get().flush();
    }
  },

  flush: async () => {
    const { events } = get();
    if (!events.length) return;
    const { token } = useAuthStore.getState();
    if (!token) return;
    const toSend = [...events];
    set({ events: [] });
    try {
      await fetch("/api/events/", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Token ${token}` },
        body: JSON.stringify(toSend),
      });
    } catch {}
  },
}));
