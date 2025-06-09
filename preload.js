const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// specific IPC functions from the main process.
contextBridge.exposeInMainWorld(
  'electron', {
    // Add any functions you need to expose to the renderer here
    closeApp: () => ipcRenderer.send('close-app'),
    minimizeApp: () => ipcRenderer.send('minimize-app'),
    maximizeApp: () => ipcRenderer.send('maximize-app'),
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    
    // Event listeners
    onMessage: (callback) => ipcRenderer.on('message', (event, ...args) => callback(...args)),
  }
);

// Loader ve log/hata mesajları için özel API
contextBridge.exposeInMainWorld('electronAPI', {
  // Log mesajlarını dinle
  onLogMessage: (callback) => {
    ipcRenderer.on('log-message', (event, message) => callback(message));
  },
  
  // Django bağlantısını yeniden dene
  retryConnection: () => {
    ipcRenderer.send('retry-connection');
  },
  
  // Django durumu için
  getServerStatus: () => ipcRenderer.invoke('get-server-status'),
  
  // Manuel yeniden yükleme
  reloadApp: () => ipcRenderer.send('reload-app'),
  
  // Güncellemelerle ilgili fonksiyonlar
  checkForUpdates: () => ipcRenderer.send('check-for-updates'),
  
  // Güncelleme ilerleme bilgisi için
  onUpdateProgress: (callback) => {
    ipcRenderer.on('update-progress', (event, progressObj) => callback(progressObj));
  }
}); 