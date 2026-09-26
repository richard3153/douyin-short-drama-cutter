const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const fs = require('fs');

let mainWindow = null;

// 工作目录（需要在 app ready 后才能用 app.isPackaged）
function getWorkDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'app')
    : __dirname;
}

// Python 路径
const getPythonPath = () => {
  const WORK_DIR = getWorkDir();
  const venvPython = path.join(WORK_DIR, '.venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) return venvPython;
  try {
    const which = execSync('which python3', { encoding: 'utf-8' }).trim();
    if (which) return which;
  } catch {}
  return 'python3';
};

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 480,
    height: 860,
    minWidth: 420,
    minHeight: 700,
    maxWidth: 520,
    title: '短剧剪辑工作站',
    backgroundColor: '#0a0a0f',
    trafficLightPosition: { x: 16, y: 16 },
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile('index.html');

  // 开发模式打开 DevTools
  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ========== IPC Handlers ==========

// 状态查询
ipcMain.handle('get-status', async () => {
  const WORK_DIR = getWorkDir();
  const python = getPythonPath();
  const dirs = {
    raw: path.join(WORK_DIR, 'raw_videos'),
    bgm: path.join(WORK_DIR, 'bgm'),
    output: path.join(WORK_DIR, 'output_videos'),
    narration: path.join(WORK_DIR, 'narration'),
  };

  const rawVideos = [];
  const dramas = {};

  if (fs.existsSync(dirs.raw)) {
    scanDir(dirs.raw, rawVideos, dramas, dirs.raw);
  }

  const dramaList = Object.entries(dramas).map(([name, files]) => ({
    name,
    count: files.length,
    files: files.sort(naturalSort),
  }));

  const bgmFiles = safeListDir(dirs.bgm, ['.mp3', '.wav', '.flac', '.ogg', '.m4a']);
  const outputFiles = safeListDir(dirs.output, ['.mp4']);
  const narrFiles = safeListDir(dirs.narration, ['.mp3']);

  return {
    dramas: dramaList,
    raw_videos: rawVideos.sort(naturalSort),
    raw_count: rawVideos.length,
    bgm_files: bgmFiles,
    bgm_count: bgmFiles.length,
    outputs: outputFiles,
    output_count: outputFiles.length,
    narration_files: narrFiles,
    narration_count: narrFiles.length,
    python: python,
    workDir: WORK_DIR,
  };
});

// 扫描目录（支持子目录）
function scanDir(dir, allFiles, dramas, baseDir) {
  if (!fs.existsSync(dir)) return;
  const items = fs.readdirSync(dir, { withFileTypes: true });
  for (const item of items) {
    const fullPath = path.join(dir, item.name);
    if (item.isDirectory()) {
      scanDir(fullPath, allFiles, dramas, baseDir);
    } else if (/\.(mp4|mov|avi|mkv|flv|wmv|webm)$/i.test(item.name)) {
      const rel = path.relative(baseDir, fullPath);
      allFiles.push(rel);

      // 判断是否在子目录中
      const parts = rel.split(path.sep);
      if (parts.length > 1) {
        const dramaName = parts[0];
        if (!dramas[dramaName]) dramas[dramaName] = [];
        dramas[dramaName].push(parts.slice(1).join(path.sep));
      } else {
        if (!dramas['根目录']) dramas['根目录'] = [];
        dramas['根目录'].push(item.name);
      }
    }
  }
}

function safeListDir(dir, exts) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(f => exts.some(ext => f.toLowerCase().endsWith(ext)))
    .sort(naturalSort);
}

function naturalSort(a, b) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

// 运行处理
ipcMain.handle('run-processing', async (event, mode) => {
  const WORK_DIR = getWorkDir();
  const python = getPythonPath();
  const script = mode === 'trailer'
    ? 'trailer_generator.py'
    : 'ai_short_video_cutter_pro.py';
  const logFile = mode === 'trailer'
    ? 'trailer_processing.log'
    : 'processing.log';
  const logPath = path.join(WORK_DIR, logFile);

  const proc = spawn(python, [script], {
    cwd: WORK_DIR,
    env: { ...process.env },
  });

  // 清空日志
  fs.writeFileSync(logPath, '');

  // 实时写日志
  proc.stdout.on('data', (data) => {
    const text = data.toString();
    fs.appendFileSync(logPath, text);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('log-data', text);
    }
  });

  proc.stderr.on('data', (data) => {
    const text = data.toString();
    fs.appendFileSync(logPath, text);
  });

  proc.on('close', (code) => {
    const time = new Date().toLocaleTimeString('zh-CN');
    fs.appendFileSync(logPath, `\n[${time}] 处理完成，退出码: ${code}\n`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('process-done', { code, mode });
    }
  });

  return { ok: true, message: `已启动${mode === 'trailer' ? '预告片' : '正片'}生成` };
});

// 读取日志
ipcMain.handle('get-log', async (event, mode) => {
  const WORK_DIR = getWorkDir();
  const logFile = mode === 'trailer'
    ? 'trailer_processing.log'
    : 'processing.log';
  const logPath = path.join(WORK_DIR, logFile);

  if (fs.existsSync(logPath)) {
    const content = fs.readFileSync(logPath, 'utf-8');
    return { log: content.split('\n').slice(-100).join('\n') };
  }
  return { log: '' };
});

// 打开文件夹
ipcMain.handle('open-folder', async (event, folder) => {
  const WORK_DIR = getWorkDir();
  const folderMap = {
    raw: 'raw_videos',
    bgm: 'bgm',
    output: 'output_videos',
    narration: 'narration',
    subtitles: 'subtitles',
  };
  const dir = path.join(WORK_DIR, folderMap[folder] || folder);
  if (fs.existsSync(dir)) {
    shell.openPath(dir);
    return { ok: true };
  }
  return { ok: false, error: '目录不存在' };
});

// 选择文件夹（导入视频）
ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'multiSelections'],
    title: '选择视频文件夹',
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return { ok: true, paths: result.filePaths };
  }
  return { ok: false };
});

// ========== App Lifecycle ==========

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  app.quit();
});
