import { create } from 'zustand';

interface Project {
  path: string;
  name: string;
  active: boolean;
  lastBackup?: string;
  backupCount: number;
  size: number;
}

interface ProjectStore {
  projects: Project[];
  loading: boolean;
  error: string | null;

  setProjects: (projects: Project[]) => void;
  loadProjects: () => Promise<void>;
  addProject: (path: string) => Promise<void>;
  removeProject: (path: string) => Promise<void>;
  toggleProject: (path: string, active: boolean) => Promise<void>;
  refreshProjects: () => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  loading: false,
  error: null,

  setProjects: (projects) => set({ projects }),

  loadProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await window.saviorAPI.getProjects();
      set({ projects, loading: false });
    } catch (error: any) {
      set({ error: error?.message || 'Failed to load projects', loading: false });
    }
  },

  addProject: async (path: string) => {
    try {
      await window.saviorAPI.addProject(path);
      await get().loadProjects();
    } catch (error: any) {
      set({ error: error?.message || 'Failed to add project' });
    }
  },

  removeProject: async (path: string) => {
    try {
      await window.saviorAPI.removeProject(path);
      await get().loadProjects();
    } catch (error: any) {
      set({ error: error?.message || 'Failed to add project' });
    }
  },

  toggleProject: async (path: string, active: boolean) => {
    try {
      if (active) {
        await window.saviorAPI.watchProject(path);
      } else {
        await window.saviorAPI.stopProject(path);
      }
      await get().loadProjects();
    } catch (error: any) {
      set({ error: error?.message || 'Failed to add project' });
    }
  },

  refreshProjects: async () => {
    await get().loadProjects();
  }
}));