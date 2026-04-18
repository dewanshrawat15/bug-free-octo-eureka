import { create } from "zustand";
import { api } from "../api/client";

export const useSessionStore = create((set, get) => ({
  session: null,
  status: null,
  currentRound: 0,
  isLoading: false,

  startSession: async () => {
    set({ isLoading: true });
    try {
      const data = await api.post("/api/sessions/", {});
      set({ session: data, status: data.status, currentRound: data.current_round, isLoading: false });
      return data;
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  fetchSession: async (sessionId) => {
    const data = await api.get(`/api/sessions/${sessionId}/`);
    set({ session: data, status: data.status, currentRound: data.current_round });
    return data;
  },

  setStatus: (status) => set({ status }),
  setRound: (round) => set({ currentRound: round }),

  submitGoal: async (sessionId, goal) => {
    const data = await api.post(`/api/sessions/${sessionId}/goal/`, goal);
    set({ status: "PATH_PRESENTED", currentRound: 1 });
    return data;
  },

  pathAction: async (sessionId, payload) => {
    const data = await api.post(`/api/sessions/${sessionId}/path-action/`, payload);
    if (data.status === "CLOSED") set({ status: "CLOSED" });
    if (data.round) set({ currentRound: data.round });
    return data;
  },

  clear: () => set({ session: null, status: null, currentRound: 0 }),
}));
