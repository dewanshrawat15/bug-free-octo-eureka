import { create } from "zustand";

export const usePathStore = create((set, get) => ({
  pathSets: [],
  selectedPath: null,
  forcedClose: null,

  addPathSet: (round, paths) =>
    set((s) => ({
      pathSets: [...s.pathSets.filter((ps) => ps.round !== round), { round, paths }],
    })),

  currentPaths: () => {
    const { pathSets } = get();
    if (!pathSets.length) return [];
    return pathSets[pathSets.length - 1].paths;
  },

  selectPath: (path) => set({ selectedPath: path }),
  setForcedClose: (msg) => set({ forcedClose: msg }),

  clear: () => set({ pathSets: [], selectedPath: null, forcedClose: null }),
}));
