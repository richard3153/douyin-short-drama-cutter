// ============================================
// 短剧剪辑工作站 v3.0 - 前端逻辑
// 支持 Electron 桌面 + 浏览器 Web 双模式
// ============================================

const IS_ELECTRON = !!(window.electronAPI);

let isRunning = false;
let logTimer = null;
let currentMode = 'main';
let allDramas = [];          // 全部剧目
let selectedDramas = new Set(); // 已选剧目（Set 存名称）

// 配置默认值
const DEFAULT_CONFIG = {
  aspectRatio: '9:16',
  titleDur: 1.2,
  endDur: 1.6,
  subtitleLang: 'zh',
  asrModel: 'medium',
  origVol: 0.2,
  bgmVol: 0.3,
  narrVol: 1.0,
};

// ---------- API 适配层 ----------
const api = {
  async getStatus() {
    if (IS_ELECTRON) return window.electronAPI.getStatus();
    const res = await fetch('/api/status');
    return res.json();
  },

  async runProcessing(mode, body = {}) {
    if (IS_ELECTRON) return window.electronAPI.runProcessing(mode);
    const endpoint = mode === 'trailer' ? '/api/run-trailer' : '/api/run';
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  },

  async getLog(mode) {
    if (IS_ELECTRON) return window.electronAPI.getLog(mode);
    const endpoint = mode === 'trailer' ? '/api/log-trailer' : '/api/log';
    const res = await fetch(endpoint);
    return res.json();
  },

  async openFolder(folder) {
    if (IS_ELECTRON) return window.electronAPI.openFolder(folder);
    await fetch(`/api/open-folder?folder=${folder}`, { method: 'POST' });
    return { ok: true };
  },
};

// ---------- 初始化 ----------
document.addEventListener('DOMContentLoaded', () => {
  refreshStatus();
  setInterval(refreshStatus, 5000);
  initConfigListeners();

  // Electron 实时日志
  if (IS_ELECTRON) {
    window.electronAPI.onLogData((text) => {
      text.split('\n').forEach(line => {
        if (!line.trim()) return;
        let cls = 'log-info';
        if (line.includes('✅') || line.includes('完成') || line.includes('成功')) cls = 'log-ok';
        else if (line.includes('⚠') || line.includes('警告')) cls = 'log-warn';
        else if (line.includes('❌') || line.includes('错误') || line.includes('失败')) cls = 'log-error';
        addLog(line, cls);
      });
    });

    window.electronAPI.onProcessDone((data) => {
      const modeText = data.mode === 'trailer' ? '预告片' : '正片';
      if (data.code === 0) {
        addLog(`🎉 ${modeText}生成完成！`, 'ok');
        api.openFolder('output');
      } else {
        addLog(`❌ ${modeText}生成失败，退出码: ${data.code}`, 'error');
      }
      resetBtn();
      refreshStatus();
    });
  }

  updateTitle();
});

function updateTitle() {
  const subtitle = document.querySelector('.subtitle');
  if (subtitle) {
    subtitle.textContent = IS_ELECTRON
      ? '桌面版 · 智能剪辑 · AI解说'
      : '智能剪辑 · AI解说 · 全自动';
  }
}

// ---------- 配置初始化 ----------



// ---------- 状态刷新 ----------
async function refreshStatus() {
  try {
    const data = await api.getStatus();

    document.getElementById('badgeRaw').textContent = data.raw_count;
    document.getElementById('badgeBgm').textContent = data.bgm_count;
    document.getElementById('badgeOut').textContent = data.output_count;
    document.getElementById('badgeNarr').textContent = data.narration_count || 0;

    renderFileList('rawList', data.raw_videos, 'video');
    renderFileList('bgmList', data.bgm_files, 'audio');
    renderFileList('outList', data.outputs, 'output');

    document.getElementById('rawCount').textContent = data.raw_count;
    document.getElementById('bgmCount').textContent = data.bgm_count;
    document.getElementById('outCount').textContent = data.output_count;

    renderDramas(data.dramas || []);
  } catch (e) {
    console.error('刷新失败:', e);
  }
}

function renderDramas(dramas) {
  const el = document.getElementById('dramaList');
  const section = document.getElementById('dramaSection');

  if (!dramas || dramas.length === 0) {
    section.style.display = 'none';
    allDramas = [];
    selectedDramas.clear();
    return;
  }

  section.style.display = 'block';
  allDramas = dramas;

  el.innerHTML = dramas.map((d, i) => `
    <div class="drama-card${selectedDramas.has(d.name) ? ' selected' : ''}" 
         data-name="${d.name}" data-index="${i}"
         onclick="toggleDrama(this, '${d.name.replace(/'/g, "\\'")}')">
      <div class="drama-check">✓</div>
      <div class="drama-icon">📺</div>
      <div class="drama-info">
        <div class="drama-name">${d.name}</div>
        <div class="drama-meta">${d.count} 个视频</div>
      </div>
      <div class="drama-badge">${d.count}集</div>
    </div>
  `).join('');

  updateSelCount();
}

// ---------- 剧目选择 ----------
function toggleDrama(el, name) {
  if (isRunning) return;
  if (selectedDramas.has(name)) {
    selectedDramas.delete(name);
    el.classList.remove('selected');
  } else {
    selectedDramas.add(name);
    el.classList.add('selected');
  }
  updateSelCount();
}

function selectAllDramas() {
  if (isRunning) return;
  dramas = allDramas;
  selectedDramas = new Set(dramas.map(d => d.name));
  document.querySelectorAll('.drama-card').forEach(c => c.classList.add('selected'));
  updateSelCount();
}

function selectNoneDramas() {
  if (isRunning) return;
  selectedDramas.clear();
  document.querySelectorAll('.drama-card').forEach(c => c.classList.remove('selected'));
  updateSelCount();
}

function reverseSelectDramas() {
  if (isRunning) return;
  allDramas.forEach(d => {
    if (selectedDramas.has(d.name)) {
      selectedDramas.delete(d.name);
    } else {
      selectedDramas.add(d.name);
    }
  });
  document.querySelectorAll('.drama-card').forEach(c => {
    const name = c.dataset.name;
    c.classList.toggle('selected', selectedDramas.has(name));
  });
  updateSelCount();
}

function updateSelCount() {
  const el = document.getElementById('dramaSelCount');
  if (!el) return;
  const n = selectedDramas.size;
  el.textContent = `已选 ${n} 部`;
  el.style.color = n > 0 ? 'var(--accent)' : 'var(--text3)';
}

function renderFileList(elId, files, type) {
  const el = document.getElementById(elId);
  if (!files || files.length === 0) {
    const hints = {
      rawList: '将视频拖入 <code>raw_videos/</code>',
      bgmList: '将BGM放入 <code>bgm/</code>',
      outList: '处理完成后出现在这里',
    };
    el.innerHTML = `<div class="empty-hint">${hints[elId] || ''}</div>`;
    return;
  }

  const icons = { video: '🎬', audio: '🎵', output: '🎞️' };
  el.innerHTML = files.map(f => {
    const name = f.length > 30 ? f.slice(0, 26) + '…' + f.slice(-4) : f;
    const ext = f.split('.').pop().toLowerCase();
    return `<div class="file-item" title="${f}">
      <span class="fi-icon">${icons[type]}</span>
      <span class="fi-name">${name}</span>
      <span class="fi-ext">${ext}</span>
    </div>`;
  }).join('');
}

// ---------- 日志 ----------
async function refreshLog() {
  try {
    const data = await api.getLog(currentMode);
    const logEl = document.getElementById('consoleLog');
    logEl.innerHTML = '';

    if (!data.log) {
      addLog('暂无日志', 'info');
      return;
    }

    data.log.split('\n').forEach(line => {
      if (!line.trim()) return;
      let cls = 'log-info';
      if (line.includes('✅') || line.includes('完成') || line.includes('成功')) cls = 'log-ok';
      else if (line.includes('⚠') || line.includes('警告') || line.includes('跳过')) cls = 'log-warn';
      else if (line.includes('❌') || line.includes('错误') || line.includes('失败')) cls = 'log-error';
      addLog(line, cls);
    });

    logEl.scrollTop = logEl.scrollHeight;
  } catch (e) {
    addLog('日志获取失败: ' + e.message, 'error');
  }
}

function addLog(text, cls = 'log-info') {
  const logEl = document.getElementById('consoleLog');
  const div = document.createElement('div');
  div.className = `log-line ${cls}`;
  div.textContent = text;
  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;
}

// 配置面板已移除（AI全自动化）


// ---------- 获取当前配置 ----------
function getCurrentConfig() {
  // 所有配置项均由AI自动控制，frontend仅传递已选剧目
  return {};
}

// ---------- 开始剪辑 ----------
async function runProcessing(mode = 'main') {
  if (isRunning) return;

  // 检查是否有选中剧目
  const selected = Array.from(selectedDramas);
  if (allDramas.length > 0 && selected.length === 0) {
    addLog('⚠️ 请先在剧目列表中选择要处理的剧（点击卡片选中）', 'warn');
    return;
  }

  const btnRun = document.getElementById('btnRun');
  const btnTrailer = document.getElementById('btnTrailer');
  const btnText = document.getElementById('btnText');
  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');

  isRunning = true;
  currentMode = mode;
  btnRun.classList.add('running');
  btnRun.disabled = true;
  btnTrailer.disabled = true;

  const modeText = mode === 'trailer' ? '预告片' : '正片';
  btnText.textContent = `剪辑${modeText}中…`;
  dot.classList.add('running');
  statusText.textContent = `剪辑${modeText}中`;

  // 获取当前配置
  const config = getCurrentConfig();
  console.log('当前配置:', config);

  const selText = selected.length > 0
    ? `（${selected.length}部: ${selected.join(', ')}）`
    : '（全量）';
  addLog(`🚀 开始生成${modeText} ${selText}...`, 'info');

  try {
    const config = getCurrentConfig();
    const data = await api.runProcessing(mode, { selected_dramas: selected, ...config });

    if (data.ok) {
      addLog(data.message || `开始处理...`, 'info');

      if (!IS_ELECTRON) {
        if (logTimer) clearInterval(logTimer);
        logTimer = setInterval(refreshLog, 3000);
      }
    } else {
      addLog('❌ ' + (data.error || '启动失败'), 'error');
      resetBtn();
    }
  } catch (e) {
    addLog('❌ 错误: ' + e.message, 'error');
    resetBtn();
  }
}

// 自动检测完成
let lastOutputCount = 0;
async function checkDone() {
  if (!isRunning || IS_ELECTRON) return;
  try {
    const data = await api.getStatus();
    if (data.output_count > lastOutputCount && lastOutputCount > 0) {
      lastOutputCount = data.output_count;
      addLog(`🎉 新成片已生成！共 ${data.output_count} 个`, 'ok');
      resetBtn();
    } else {
      lastOutputCount = data.output_count;
    }
  } catch (e) {}
}
setInterval(checkDone, 5000);

function resetBtn() {
  isRunning = false;
  const btnRun = document.getElementById('btnRun');
  const btnTrailer = document.getElementById('btnTrailer');
  const btnText = document.getElementById('btnText');
  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');

  btnRun.classList.remove('running');
  btnRun.disabled = false;
  btnTrailer.disabled = false;
  btnText.textContent = '剪辑正片';
  dot.classList.remove('running');
  statusText.textContent = '就绪';
  if (logTimer) { clearInterval(logTimer); logTimer = null; }
}

// ---------- 打开文件夹 ----------
async function openFolder(folder) {
  try {
    await api.openFolder(folder);
  } catch (e) {
    console.error('打开文件夹失败:', e);
  }
}

// ---------- 预览 ----------
function previewVideo() {
  addLog('👁️ 预览功能开发中...', 'info');
  // TODO: 实现视频预览功能
}

// ---------- 保存配置 ----------
async function saveConfig() {
  const config = getCurrentConfig();
  try {
    const res = await fetch('/api/save-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const data = await res.json();
    if (data.ok) {
      addLog('✅ 配置已保存', 'ok');
    } else {
      addLog('❌ 保存失败: ' + data.error, 'error');
    }
  } catch (e) {
    console.error('保存配置失败:', e);
  }
}

// 页面离开时自动保存
window.addEventListener('beforeunload', () => {
  saveConfig();
});

