import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "../api/client";

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      signup: async (email, password, name) => {
        const data = await api.post("/api/auth/signup/", { email, password, name });
        set({ token: data.token, user: { id: data.user_id, email }, isAuthenticated: true });
        return data;
      },

      login: async (email, password) => {
        const data = await api.post("/api/auth/login/", { email, password });
        set({ token: data.token, user: { id: data.user_id, email }, isAuthenticated: true });
        return data;
      },

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false });
      },
    }),
    { name: "auth-storage", partialize: (s) => ({ token: s.token, user: s.user, isAuthenticated: s.isAuthenticated }) }
  )
);
