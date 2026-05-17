import create from "zustand";
import api from "../api/client";

type User = {
  id: string;
  username?: string;
  email?: string;
};

type AuthState = {
  user: User | null;
  token: string | null;
  loading: boolean;
  error?: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("token"),
  loading: false,
  error: null,
  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const resp = await api.post("/auth/login", { username: email, password });
      const token = resp.data.access_token || resp.data.token;
      if (!token) throw new Error("No token returned from server");
      localStorage.setItem("token", token);
      set({ token, user: resp.data.user || null, loading: false });
    } catch (err: any) {
      set({ loading: false, error: err?.response?.data?.detail || err.message });
      throw err;
    }
  },
  register: async (username, email, password) => {
    set({ loading: true, error: null });
    try {
      await api.post("/auth/register", { username, email, password });
      set({ loading: false });
    } catch (err: any) {
      set({ loading: false, error: err?.response?.data?.detail || err.message });
      throw err;
    }
  },
  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null });
    try {
      window.location.href = "/login";
    } catch (e) {
      // noop
    }
  },
}));
