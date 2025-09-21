import { create } from 'zustand';

interface Settings {
  theme: 'dark' | 'light';
  autoStart: boolean;
  notifications: boolean;
  interval: number;
  compression: number;
  smartMode: boolean;
  incremental: boolean;
  excludeGit: boolean;
  cloudSync: boolean;
  showInDock: boolean;
  minimizeToTray: boolean;
}

interface SettingsStore {
  settings: Settings;
  loading: boolean;

  loadSettings: () => Promise<void>;
  updateSettings: (settings: Partial<Settings>) => Promise<void>;
  resetSettings: () => Promise<void>;
}

const defaultSettings: Settings = {
  theme: 'dark',
  autoStart: false,
  notifications: true,
  interval: 20,
  compression: 6,
  smartMode: true,
  incremental: true,
  excludeGit: false,
  cloudSync: false,
  showInDock: true,
  minimizeToTray: true
};

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: defaultSettings,
  loading: false,

  loadSettings: async () => {
    set({ loading: true });
    try {
      const settings = await window.saviorAPI.getSettings();
      set({ settings, loading: false });
    } catch (error) {
      console.error('Failed to load settings:', error);
      set({ loading: false });
    }
  },

  updateSettings: async (newSettings: Partial<Settings>) => {
    const updatedSettings = { ...get().settings, ...newSettings };
    set({ settings: updatedSettings });

    try {
      await window.saviorAPI.updateSettings(updatedSettings);
    } catch (error) {
      console.error('Failed to save settings:', error);
      // Revert on error
      await get().loadSettings();
    }
  },

  resetSettings: async () => {
    set({ settings: defaultSettings });
    try {
      await window.saviorAPI.updateSettings(defaultSettings);
    } catch (error) {
      console.error('Failed to reset settings:', error);
    }
  }
}));