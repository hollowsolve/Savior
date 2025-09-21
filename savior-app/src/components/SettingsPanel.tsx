import React from 'react';
import { Switch } from '@headlessui/react';
import { useSettingsStore } from '../stores/settingsStore';

export const SettingsPanel: React.FC = () => {
  const { settings, updateSettings, resetSettings } = useSettingsStore();

  return (
    <div className="w-full h-full flex items-start justify-center p-8 overflow-auto">
      <div className="w-full max-w-3xl">
        <h2 className="text-3xl font-bold text-white mb-8 text-center">Settings</h2>

        <div className="space-y-6">
          {/* General Settings */}
          <section className="glass-card p-6">
            <h3 className="text-xl font-semibold text-white mb-4 text-center">General</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Theme</label>
                  <p className="text-sm text-gray-400">Choose your preferred color scheme</p>
                </div>
                <select
                  value={settings.theme}
                  onChange={(e) => updateSettings({ theme: e.target.value as 'dark' | 'light' })}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white min-w-[120px]"
                >
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Auto-start</label>
                  <p className="text-sm text-gray-400">Start Savior when your computer starts</p>
                </div>
                <Switch
                  checked={settings.autoStart}
                  onChange={(checked) => updateSettings({ autoStart: checked })}
                  className={`${
                    settings.autoStart ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.autoStart ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Notifications</label>
                  <p className="text-sm text-gray-400">Show notifications for backup events</p>
                </div>
                <Switch
                  checked={settings.notifications}
                  onChange={(checked) => updateSettings({ notifications: checked })}
                  className={`${
                    settings.notifications ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.notifications ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>
            </div>
          </section>

          {/* Backup Settings */}
          <section className="glass-card p-6">
            <h3 className="text-xl font-semibold text-white mb-4 text-center">Backup Configuration</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Backup Interval</label>
                  <p className="text-sm text-gray-400">Minutes between automatic backups</p>
                </div>
                <input
                  type="number"
                  value={settings.interval}
                  onChange={(e) => updateSettings({ interval: parseInt(e.target.value) })}
                  min="5"
                  max="120"
                  className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 w-20 text-white text-center"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Compression Level</label>
                  <p className="text-sm text-gray-400">0 = no compression, 9 = maximum</p>
                </div>
                <input
                  type="number"
                  value={settings.compression}
                  onChange={(e) => updateSettings({ compression: parseInt(e.target.value) })}
                  min="0"
                  max="9"
                  className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 w-20 text-white text-center"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Smart Mode</label>
                  <p className="text-sm text-gray-400">Wait for inactivity before backing up</p>
                </div>
                <Switch
                  checked={settings.smartMode}
                  onChange={(checked) => updateSettings({ smartMode: checked })}
                  className={`${
                    settings.smartMode ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.smartMode ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Incremental Backups</label>
                  <p className="text-sm text-gray-400">Only save changes to reduce storage</p>
                </div>
                <Switch
                  checked={settings.incremental}
                  onChange={(checked) => updateSettings({ incremental: checked })}
                  className={`${
                    settings.incremental ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.incremental ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Exclude Git Directory</label>
                  <p className="text-sm text-gray-400">Don't backup .git folders to save space</p>
                </div>
                <Switch
                  checked={settings.excludeGit}
                  onChange={(checked) => updateSettings({ excludeGit: checked })}
                  className={`${
                    settings.excludeGit ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.excludeGit ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>
            </div>
          </section>

          {/* App Settings */}
          <section className="glass-card p-6">
            <h3 className="text-xl font-semibold text-white mb-4 text-center">Application</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Show in Dock</label>
                  <p className="text-sm text-gray-400">Show Savior icon in the dock</p>
                </div>
                <Switch
                  checked={settings.showInDock}
                  onChange={(checked) => updateSettings({ showInDock: checked })}
                  className={`${
                    settings.showInDock ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.showInDock ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex-1 mr-4">
                  <label className="font-medium text-white block">Minimize to Tray</label>
                  <p className="text-sm text-gray-400">Keep running in system tray when closed</p>
                </div>
                <Switch
                  checked={settings.minimizeToTray}
                  onChange={(checked) => updateSettings({ minimizeToTray: checked })}
                  className={`${
                    settings.minimizeToTray ? 'bg-blue-600' : 'bg-gray-600'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
                >
                  <span
                    className={`${
                      settings.minimizeToTray ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>
            </div>
          </section>

          {/* Action Buttons */}
          <div className="flex justify-center gap-3 pt-6 pb-8">
            <button
              onClick={resetSettings}
              className="px-6 py-2.5 text-gray-400 hover:text-white border border-gray-600 hover:border-gray-500 rounded-lg transition-all font-medium"
            >
              Reset to Defaults
            </button>
            <button
              onClick={() => updateSettings(settings)}
              className="px-8 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all font-medium shadow-lg hover:shadow-xl"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};