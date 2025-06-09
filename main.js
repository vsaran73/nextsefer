const { app, BrowserWindow, dialog, Menu, Tray, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = require('electron-is-dev');
const fs = require('fs');
const find = require('find-process');
const http = require('http');
const waitOn = require('wait-on');
const { autoUpdater } = require('electron-updater');

// Keep references to prevent garbage collection
let mainWindow = null;
let tray = null;
let djangoProcess = null;
let djangoPort = 8000;
let appRoot = app.getAppPath();

// Loglama ayarları
let DEBUG = true; // Hata ayıklama modunu etkinleştir

// Check if another instance is running
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  console.log('Another instance is already running. Quitting...');
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance, we should focus our window
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// Log dosyası için yapılandırma
const logPath = path.join(app.getPath('userData'), 'electron_django.log');
function logMessage(message) {
  const timestamp = new Date().toISOString();
  const logEntry = `[${timestamp}] ${message}\n`;
  fs.appendFileSync(logPath, logEntry, { flag: 'a' });
  console.log(message);
  
  // Eğer pencere açıksa arayüze de log mesajı gönder
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('log-message', message);
  }
}

// Başlangıçta log dosyasını temizle
function clearLog() {
  try {
    fs.writeFileSync(logPath, '', { flag: 'w' });
    logMessage('Log file cleared');
  } catch (error) {
    console.error('Failed to clear log file:', error);
  }
}

// Django sunucusunu başlat
function startDjangoServer() {
  return new Promise((resolve, reject) => {
    logMessage('Starting Django server...');
    
    // Önce python_dist konumunu kontrol et
    let pythonExecutable;
    let pythonDistPath;
    
    if (isDev) {
      // Development modunda mevcut Python kullan
      pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
      pythonDistPath = path.join(appRoot);
      logMessage(`Development mode, using local Python: ${pythonExecutable}`);
      logMessage(`Working directory: ${pythonDistPath}`);
    } else {
      // Production modunda python_dist dizinindeki Python'u kullan
      logMessage('Production mode, checking resources path for python_dist');
      logMessage(`App path: ${appRoot}`);
      logMessage(`Resources path: ${process.resourcesPath}`);
      
      // Olası python_dist konumlarını kontrol et
      const possiblePaths = [
        path.join(process.resourcesPath, 'python_dist'),
        path.join(appRoot, 'python_dist'),
        path.join(process.resourcesPath, 'app.asar.unpacked', 'python_dist'),
        path.join(app.getAppPath(), '..', 'python_dist'),
        path.join(app.getPath('exe'), '..', 'python_dist'),
        path.join(app.getPath('exe'), '..', 'resources', 'python_dist'),
        // Program Files konumu
        path.join(process.env.ProgramFiles, 'NextSefer', 'resources', 'python_dist'),
        // Program Files (x86) konumu
        path.join(process.env.ProgramFiles, 'NextSefer', 'resources', 'app.asar.unpacked', 'python_dist'),
        // Kurulum dizini (daha fazla olası konum)
        path.join(app.getAppPath(), 'resources', 'python_dist'),
        path.join(path.dirname(app.getPath('exe')), 'python_dist')
      ];
      
      // Tüm olası konumları listele ve detaylı bilgi ver
      logMessage('Possible python_dist locations:');
      possiblePaths.forEach((testPath, index) => {
        logMessage(`[${index}] ${testPath} - Exists: ${fs.existsSync(testPath) ? 'YES' : 'NO'}`);
      });
      
      let foundPath = null;
      for (const testPath of possiblePaths) {
        logMessage(`Checking path: ${testPath}`);
        if (fs.existsSync(testPath)) {
          logMessage(`Found python_dist at: ${testPath}`);
          // Klasör içeriğini listeleyelim
          try {
            const files = fs.readdirSync(testPath);
            logMessage(`Contents of ${testPath}: ${JSON.stringify(files)}`);
          } catch (err) {
            logMessage(`Error listing directory ${testPath}: ${err.message}`);
          }
          
          // Python.exe var mı kontrol et
          const pythonExe = path.join(testPath, process.platform === 'win32' ? 'python.exe' : 'python');
          if (fs.existsSync(pythonExe)) {
            logMessage(`Found Python executable at: ${pythonExe}`);
            foundPath = testPath;
            break;
          } else {
            logMessage(`Python executable not found at: ${pythonExe}`);
          }
        }
      }
      
      if (!foundPath) {
        logMessage('ERROR: python_dist not found in any expected locations');
        
        // Acil durumda start_django.bat dosyasını oluştur ve çalıştır
        const emergencyBatchPath = path.join(app.getPath('temp'), 'start_django.bat');
        logMessage(`Creating emergency batch file at: ${emergencyBatchPath}`);
        
        try {
          // Batch dosyası içeriği
          const batchContent = `@echo off
echo Starting Django Server from emergency batch file
cd /d "%~dp0"
set PATH=%PATH%;C:\\Windows\\System32
python -m http.server 8000
`;
          
          fs.writeFileSync(emergencyBatchPath, batchContent);
          logMessage(`Created emergency batch file: ${emergencyBatchPath}`);
          
          // Batch dosyasını çalıştır
          try {
            djangoProcess = spawn('cmd.exe', ['/c', emergencyBatchPath], {
              detached: true,
              cwd: path.dirname(emergencyBatchPath),
            });
            
            logMessage(`Started emergency Django server with PID: ${djangoProcess.pid}`);
            
            // Çıktıları logla
            djangoProcess.stdout.on('data', (data) => {
              logMessage(`[Emergency Django] ${data.toString().trim()}`);
            });
            
            djangoProcess.stderr.on('data', (data) => {
              logMessage(`[Emergency Django ERROR] ${data.toString().trim()}`);
            });
            
            setTimeout(() => {
              logMessage('Emergency server should be starting, continuing...');
              resolve();
            }, 3000);
            
            return;
          } catch (err) {
            logMessage(`Error starting emergency batch file: ${err.message}`);
          }
        } catch (err) {
          logMessage(`Error creating emergency batch file: ${err.message}`);
        }
        
        // Kurulum ve sistem hakkında detaylı bilgi topla
        try {
          logMessage('----- SYSTEM INFO -----');
          logMessage(`App path: ${appRoot}`);
          logMessage(`Exe path: ${app.getPath('exe')}`);
          logMessage(`Resources path: ${process.resourcesPath}`);
          logMessage(`Temp path: ${app.getPath('temp')}`);
          logMessage(`User data path: ${app.getPath('userData')}`);
          logMessage(`Platform: ${process.platform} (${process.arch})`);
          logMessage(`Windows version: ${process.getSystemVersion()}`);
          
          // Klasör dizini listele
          const exeDir = path.dirname(app.getPath('exe'));
          logMessage(`Contents of exe dir (${exeDir}):`);
          try {
            const exeContents = fs.readdirSync(exeDir);
            logMessage(JSON.stringify(exeContents));
          } catch (err) {
            logMessage(`Error listing exe dir: ${err.message}`);
          }
          
          // Resources dizini listele
          logMessage(`Contents of resources path (${process.resourcesPath}):`);
          try {
            const resourcesContents = fs.readdirSync(process.resourcesPath);
            logMessage(JSON.stringify(resourcesContents));
            
            // Resources/app.asar.unpacked dizini var mı?
            const unpackedPath = path.join(process.resourcesPath, 'app.asar.unpacked');
            if (fs.existsSync(unpackedPath)) {
              logMessage(`Contents of unpacked path (${unpackedPath}):`);
              const unpackedContents = fs.readdirSync(unpackedPath);
              logMessage(JSON.stringify(unpackedContents));
            }
          } catch (err) {
            logMessage(`Error listing resources dir: ${err.message}`);
          }
          
          logMessage('----- END SYSTEM INFO -----');
        } catch (err) {
          logMessage(`Error getting system info: ${err.message}`);
        }
        
        return reject(new Error('python_dist directory not found! Please reinstall the application.'));
      }
      
      pythonDistPath = foundPath;
      pythonExecutable = path.join(pythonDistPath, process.platform === 'win32' ? 'python.exe' : 'python');
      
      // Python çalıştırılabilir dosyası var mı kontrol et
      logMessage(`Checking Python executable: ${pythonExecutable}`);
      if (!fs.existsSync(pythonExecutable)) {
        logMessage(`ERROR: Python executable not found: ${pythonExecutable}`);
        logMessage('Contents of python_dist:');
        try {
          const distContents = fs.readdirSync(pythonDistPath);
          logMessage(JSON.stringify(distContents));
        } catch (err) {
          logMessage(`Error listing python_dist: ${err.message}`);
        }
        
        // Alternatif olarak batch dosyasını çalıştırmayı dene
        const batchPath = path.join(pythonDistPath, 'start_django.bat');
        if (fs.existsSync(batchPath)) {
          logMessage(`Found batch file, trying to use it: ${batchPath}`);
          try {
            djangoProcess = spawn('cmd.exe', ['/c', batchPath], {
              detached: true,
              cwd: pythonDistPath,
              shell: true
            });
            logMessage(`Started Django using batch file with PID: ${djangoProcess.pid}`);
            
            // Bekle ve devam et
            setTimeout(() => {
              logMessage('Django server should be starting via batch file');
              resolve();
            }, 2000);
            
            return;
          } catch (error) {
            logMessage(`Error starting batch file: ${error.message}`);
          }
        } else {
          // Batch dosyası yoksa oluştur
          logMessage(`Batch file not found, creating one at: ${batchPath}`);
          try {
            const batchContent = `@echo off
cd /d "%~dp0"
python.exe manage.py runserver 127.0.0.1:8000
`;
            fs.writeFileSync(batchPath, batchContent);
            logMessage(`Created batch file: ${batchPath}`);
            
            // Oluşturulan batch dosyasını çalıştır
            djangoProcess = spawn('cmd.exe', ['/c', batchPath], {
              detached: true,
              cwd: pythonDistPath,
              shell: true
            });
            
            logMessage(`Started Django using new batch file with PID: ${djangoProcess.pid}`);
            
            setTimeout(() => {
              logMessage('Django server should be starting via new batch file');
              resolve();
            }, 2000);
            
            return;
          } catch (err) {
            logMessage(`Error creating/running batch file: ${err.message}`);
          }
        }
        
        return reject(new Error(`Python executable not found: ${pythonExecutable}`));
      }
    }
    
    // Django sunucu konumu yolu
    const djangoScript = path.join(pythonDistPath, 'manage.py');
    logMessage(`Checking Django script: ${djangoScript}`);
    if (!fs.existsSync(djangoScript)) {
      logMessage(`ERROR: Django script not found: ${djangoScript}`);
      return reject(new Error(`Django script not found: ${djangoScript}`));
    }
    
    logMessage(`Python executable: ${pythonExecutable}`);
    logMessage(`Django script: ${djangoScript}`);
    logMessage(`Working directory: ${pythonDistPath}`);
    
    // Django sunucusunu başlat
    const djangoArgs = ['runserver', `127.0.0.1:${djangoPort}`];
    logMessage(`Running command: ${pythonExecutable} ${djangoScript} ${djangoArgs.join(' ')}`);
    
    try {
      djangoProcess = spawn(pythonExecutable, [djangoScript, ...djangoArgs], {
        cwd: pythonDistPath,
        detached: process.platform !== 'win32', // Windows dışında detached process
        env: {
          ...process.env,
          PYTHONPATH: pythonDistPath
        }
      });
      
      logMessage(`Django process started with PID: ${djangoProcess.pid}`);
    } catch (error) {
      logMessage(`Error spawning Django process: ${error.message}`);
      return reject(error);
    }
    
    // Log stdout ve stderr
    djangoProcess.stdout.on('data', (data) => {
      logMessage(`[Django] ${data.toString().trim()}`);
    });
    
    djangoProcess.stderr.on('data', (data) => {
      logMessage(`[Django ERROR] ${data.toString().trim()}`);
    });
    
    djangoProcess.on('error', (err) => {
      logMessage(`Failed to start Django: ${err.message}`);
      reject(err);
    });
    
    djangoProcess.on('close', (code) => {
      if (code !== 0 && code !== null) {
        logMessage(`Django process exited with code ${code}`);
      }
    });
    
    // Django sunucusunun hazır olmasını bekle
    logMessage(`Waiting for Django server to be ready on http://127.0.0.1:${djangoPort}`);
    
    // wait-on yerine manuel kontrol kullan
    let attempts = 0;
    const maxAttempts = 30; // 30 deneme (15 saniye)
    const checkInterval = 500; // 500ms aralıklarla kontrol et
    
    function checkServer() {
      if (attempts >= maxAttempts) {
        logMessage('Timed out waiting for Django server');
        // Server yine de çalışabilir, o yüzden reject değil resolve kullan
        resolve();
        return;
      }
      
      attempts++;
      
      const req = http.get(`http://127.0.0.1:${djangoPort}`, (res) => {
        logMessage(`Django server is ready (HTTP ${res.statusCode})`);
        res.resume();
        resolve();
      });
      
      req.on('error', () => {
        logMessage(`Waiting for Django server (attempt ${attempts}/${maxAttempts})`);
        setTimeout(checkServer, checkInterval);
      });
      
      req.setTimeout(checkInterval, () => {
        req.abort();
        logMessage(`Connection timeout (attempt ${attempts}/${maxAttempts})`);
        setTimeout(checkServer, checkInterval);
      });
    }
    
    // İlk kontrolü bir süre sonra başlat, Django'nun başlaması için zaman ver
    setTimeout(checkServer, 1000);
  });
}

// Django sunucusunun durumunu kontrol et
function checkDjangoServer() {
  return new Promise((resolve, reject) => {
    // Basit HTTP isteği ile Django'nun çalışıp çalışmadığını kontrol et
    logMessage(`Checking Django server at http://localhost:${djangoPort}/`);
    
    const req = http.get(`http://localhost:${djangoPort}/`, (res) => {
      logMessage(`Django server is running (status: ${res.statusCode})`);
      resolve(true);
      res.resume(); // Belleği boşalt
    });
    
    req.on('error', (err) => {
      logMessage(`Django server check failed: ${err.message}`);
      resolve(false);
    });
    
    // 5 saniye timeout
    req.setTimeout(5000, () => {
      logMessage('Django server check timed out');
      req.abort();
      resolve(false);
    });
  });
}

// Django hazır olduğunda gerçek uygulamayı yükle
function connectToDjango() {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const maxAttempts = 15;  // 15 deneme (15 saniye)
    
    function tryConnect() {
      if (attempts >= maxAttempts) {
        reject(new Error('Django sunucusuna bağlanılamadı - maksimum deneme sayısına ulaşıldı'));
        return;
      }
      
      attempts++;
      logMessage(`Django sunucusuna bağlanma denemesi: ${attempts}/${maxAttempts}`);
      
      const req = http.get(`http://127.0.0.1:${djangoPort}/`, (res) => {
        logMessage(`Django yanıt verdi: HTTP ${res.statusCode}`);
        res.resume();  // Belleği boşalt
        resolve();
      });
      
      req.on('error', (err) => {
        logMessage(`Deneme ${attempts} başarısız: ${err.message}`);
        setTimeout(tryConnect, 1000);  // 1 saniye sonra tekrar dene
      });
      
      req.setTimeout(1000, () => {
        logMessage(`Deneme ${attempts} zaman aşımına uğradı`);
        req.abort();
        setTimeout(tryConnect, 1000);  // 1 saniye sonra tekrar dene
      });
    }
    
    tryConnect(); // İlk denemeyi başlat
  });
}

// Main window creation
function createWindow() {
  // İkon yolunu belirle ve alternatif dosyaları kontrol et
  let iconPath = path.join(__dirname, 'icon.ico');
  
  // İkon bulunamazsa alternatif seçenekleri dene
  if (!fs.existsSync(iconPath)) {
    const pngPath = path.join(__dirname, 'icon.png');
    if (fs.existsSync(pngPath)) {
      iconPath = pngPath;
      logMessage(`Using icon from: ${iconPath}`);
    } else {
      const svgPath = path.join(__dirname, 'icon.svg');
      if (fs.existsSync(svgPath)) {
        iconPath = svgPath;
        logMessage(`Using icon from: ${iconPath}`);
      } else {
        logMessage('Window icon not found, using default Electron icon');
        iconPath = null;
      }
    }
  }
  
  // Create browser window
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: iconPath || undefined,
    show: false // Don't show until loaded
  });

  // Önce yükleme ekranını göster
  mainWindow.loadFile('loader.html');
  logMessage('Loading screen displayed');
  
  // Django bağlantısını kontrol et ve yükle
  connectToDjango()
    .then(() => {
      logMessage('Loading Django application in the window');
      mainWindow.loadURL(`http://127.0.0.1:${djangoPort}/login/`);
    })
    .catch((err) => {
      logMessage(`Failed to connect to Django: ${err.message}`);
      dialog.showErrorBox(
        'Bağlantı Hatası',
        'Django sunucusuna bağlanılamadı. Uygulama kapatılacak.'
      );
      app.quit();
    });
  
  // Pencereyi göster
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Set up dev tools in development mode
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Create system tray icon
  createTray();

  // Handle window being closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  // Create tray icon with fallback
  let iconPath = path.join(__dirname, 'icon.ico');
  
  // İkon bulunamazsa alternatif seçenekleri dene
  if (!fs.existsSync(iconPath)) {
    // Alternatif 1: PNG dosyasını dene
    const pngPath = path.join(__dirname, 'icon.png');
    if (fs.existsSync(pngPath)) {
      iconPath = pngPath;
    } else {
      // Alternatif 2: SVG dosyasını dene
      const svgPath = path.join(__dirname, 'icon.svg');
      if (fs.existsSync(svgPath)) {
        iconPath = svgPath;
      } else {
        // Alternatif 3: Electron'un kendi ikonunu kullan
        console.log('Icon not found, using default Electron icon');
        iconPath = null;
      }
    }
  }
  
    try {
    tray = iconPath ? new Tray(iconPath) : new Tray();
  } catch (error) {
    console.error('Failed to create tray icon:', error);
    tray = null;
  }
    
  // Tray null ise (oluşturulamadıysa) fonksiyondan çık
  if (!tray) {
    console.log('Tray icon could not be created, skipping tray menu setup');
    return;
  }

  // Create context menu
  const contextMenu = Menu.buildFromTemplate([
    { 
      label: 'Göster', 
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      } 
    },
    { type: 'separator' },
    { 
      label: 'Çıkış', 
      click: () => {
        app.quit();
      } 
    }
  ]);
  
  tray.setToolTip('NextSefer');
  tray.setContextMenu(contextMenu);
  
  // Double-click on tray icon shows the main window
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// Set up IPC event listeners
ipcMain.on('close-app', () => {
  app.quit();
});

ipcMain.on('minimize-app', () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});

ipcMain.on('maximize-app', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

// Yeni IPC Event Listener'lar
ipcMain.on('retry-connection', () => {
  logMessage('Manuel olarak yeniden bağlantı deneniyor');
  
  // Django sunucusunun çalıştığını kontrol et
  checkDjangoServer()
    .then(isRunning => {
      if (isRunning) {
        logMessage('Django sunucusu çalışıyor, sayfayı yeniden yüklüyorum');
        if (mainWindow) {
          mainWindow.loadURL(`http://127.0.0.1:${djangoPort}/login/`);
        }
      } else {
        // Django sunucusunu yeniden başlatmayı dene
        logMessage('Django sunucusu çalışmıyor, yeniden başlatılıyor');
        
        // Mevcut process'i öldür
        if (djangoProcess) {
          try {
            djangoProcess.kill();
            logMessage('Mevcut Django process\'i sonlandırıldı');
          } catch (err) {
            logMessage(`Process sonlandırma hatası: ${err.message}`);
          }
        }
        
        // Sunucuyu yeniden başlat
        startDjangoServer()
          .then(() => {
            logMessage('Django sunucusu başarıyla yeniden başlatıldı');
            if (mainWindow) {
              mainWindow.loadURL(`http://127.0.0.1:${djangoPort}/login/`);
            }
          })
          .catch(err => {
            logMessage(`Yeniden başlatma hatası: ${err.message}`);
            dialog.showErrorBox(
              'Sunucu Hatası',
              'Django sunucusu yeniden başlatılamadı. Lütfen uygulamayı yeniden başlatın.'
            );
          });
      }
    });
});

ipcMain.on('reload-app', () => {
  logMessage('Uygulama yeniden yükleniyor');
  if (mainWindow) {
    mainWindow.reload();
  }
});

ipcMain.handle('get-server-status', async () => {
  try {
    const isRunning = await checkDjangoServer();
    return { 
      running: isRunning,
      port: djangoPort
    };
  } catch (err) {
    return { 
      running: false,
      error: err.message
    };
  }
});

// Start app when Electron is ready
app.whenReady().then(() => {
  // Uygulama başladığında log dosyasını temizle
  clearLog();
  logMessage('Electron app starting');
  
  // Güncelleme kontrolü
  if (!isDev) {
    setupAutoUpdater();
    autoUpdater.checkForUpdates();
  }
  
  startDjangoServer()
    .then(() => {
      logMessage('Django server started successfully');
      createWindow();
    })
    .catch((error) => {
      logMessage(`Error starting Django server: ${error.message}`);
      dialog.showErrorBox(
        'Server Error',
        `Failed to start the Django server: ${error.message}`
      );
      app.quit();
    });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Auto-updater configuration
function setupAutoUpdater() {
  // Auto-updater events
  autoUpdater.logger = console;
  autoUpdater.logger.transports.file.level = 'info';
  
  // Güncelleştirici olayları
  autoUpdater.on('checking-for-update', () => {
    logMessage('Güncellemeler kontrol ediliyor...');
  });
  
  autoUpdater.on('update-available', (info) => {
    logMessage(`Güncelleme mevcut: ${info.version}`);
    
    dialog.showMessageBox({
      type: 'info',
      title: 'Güncelleme Mevcut',
      message: `NextSefer'in yeni bir sürümü mevcut: ${info.version}`,
      buttons: ['Şimdi Güncelle', 'Daha Sonra'],
      defaultId: 0
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.downloadUpdate();
      }
    });
  });
  
  autoUpdater.on('update-not-available', () => {
    logMessage('En güncel sürümü kullanıyorsunuz.');
  });
  
  autoUpdater.on('download-progress', (progressObj) => {
    let progressMessage = `İndirme hızı: ${progressObj.bytesPerSecond} - İndirilen: ${progressObj.percent}%`;
    logMessage(progressMessage);
    
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('update-progress', progressObj);
    }
  });
  
  autoUpdater.on('update-downloaded', (info) => {
    logMessage(`Güncelleme indirildi: ${info.version}`);
    
    dialog.showMessageBox({
      type: 'info',
      title: 'Güncelleme Hazır',
      message: 'Güncelleme indirildi. Uygulamayı yeniden başlatarak güncellemeleri uygulayabilirsiniz.',
      buttons: ['Şimdi Yeniden Başlat', 'Daha Sonra'],
      defaultId: 0
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.quitAndInstall(false, true);
      }
    });
  });
  
  autoUpdater.on('error', (err) => {
    logMessage(`Güncelleme hatası: ${err}`);
  });
  
  // Her saat başı güncelleme kontrolü
  setInterval(() => {
    autoUpdater.checkForUpdates();
  }, 60 * 60 * 1000);
}

// IPC event para manual update check
ipcMain.on('check-for-updates', () => {
  if (!isDev) {
    autoUpdater.checkForUpdates();
  } else {
    logMessage('Development modunda güncelleme kontrolü devre dışı.');
  }
});

// Handle window-all-closed event
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Kill Django process when app is quitting
app.on('quit', () => {
  if (djangoProcess !== null) {
    console.log('Killing Django server process');
    
    if (process.platform === 'win32') {
      // On Windows, we need to kill Django process and any child processes
      find('port', djangoPort)
        .then((list) => {
          list.forEach((proc) => {
            try {
              process.kill(proc.pid, 'SIGTERM');
              console.log(`Killed process PID: ${proc.pid}`);
            } catch (e) {
              console.error(`Failed to kill process ${proc.pid}: ${e.message}`);
            }
          });
        })
        .catch((err) => {
          console.error('Error finding processes:', err);
        });
      
      // Kill the parent process as well
      try {
        djangoProcess.kill();
      } catch (e) {
        console.error(`Failed to kill Django process: ${e.message}`);
      }
    } else {
      // On Unix-like systems, we can simply kill the process group
      try {
        process.kill(-djangoProcess.pid);
      } catch (e) {
        console.error(`Failed to kill Django process group: ${e.message}`);
      }
    }
  }
}); 