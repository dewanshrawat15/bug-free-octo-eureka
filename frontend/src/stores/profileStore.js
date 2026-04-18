import { create } from "zustand";
import { api } from "../api/client";

export const useProfileStore = create((set) => ({
  profile: null,
  persona: null,
  isLoading: false,
  error: null,

  fetchProfile: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.get("/api/profile/");
      set({ profile: data, persona: data.persona, isLoading: false });
      return data;
    } catch {
      set({ isLoading: false, error: "No profile found" });
      return null;
    }
  },

  uploadResume: async (file) => {
    set({ isLoading: true, error: null });
    try {
      const form = new FormData();
      form.append("resume", file);
      const data = await api.upload("/api/profile/upload/", form);
      set({ profile: data, persona: data.persona, isLoading: false });
      return data;
    } catch (e) {
      set({ isLoading: false, error: e.message });
      throw e;
    }
  },

  clear: () => set({ profile: null, persona: null }),
}));
