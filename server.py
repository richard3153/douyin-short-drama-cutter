#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音短剧AI剪辑工具 - 本地HTTP服务 v2.0
支持 raw_videos/剧名/ 子目录批量处理
"""

import http.server
import socketserver
import os
import json
import threading
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8765
WORK_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = "/bin/bash"
# 用 shell + source venv 确保环境正确
def _get_venv_cmd():
    """返回激活 venv 后运行 python3 的命令前缀"""
    venv_activate = str(WORK_DIR / ".venv" / "bin" / "activate")
    return f". {venv_activate} && python3"

# 计算 venv site-packages 路径（用于 PYTHONPATH）
VENV_SITE = None
_venv_lib = WORK_DIR / ".venv" / "lib"
if _venv_lib.exists():
    for _d in sorted(_venv_lib.iterdir()):
        if _d.is_dir() and _d.name.startswith("python"):
            _sp = _d / "site-packages"
            if _sp.exists():
                VENV_SITE = str(_sp)
                break
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".flv"}

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
}

def _list_files(d):
    if not d.exists():
        return []
    return sorted([f.name for f in d.iterdir()
                   if f.is_file() and not f.name.startswith(".")])

def _scan_dramas(raw_dir):
    """扫描 raw_videos/ 下的剧目结构
    返回: [{"name": "剧名", "path": "raw_videos/剧名", "count": 35}, ...]
    也支持无子目录的旧结构
    """
    if not raw_dir.exists():
        return []

    dramas = []
    # 子目录 = 各剧
    subdirs = [d for d in raw_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    for d in sorted(subdirs):
        count = len([f for f in d.iterdir() if f.suffix.lower() in VIDEO_EXTS])
        if count > 0:
            dramas.append({
                "name": d.name,
                "path": str(d),
                "count": count,
            })

    # 兼容旧结构：raw_videos/ 下直接放视频
    if not dramas:
        direct = [f for f in raw_dir.iterdir()
                  if f.suffix.lower() in VIDEO_EXTS and not f.name.startswith(".")]
        if direct:
            dramas.append({
                "name": raw_dir.name,
                "path": str(raw_dir),
                "count": len(direct),
            })

    return dramas

def _total_video_count(raw_dir):
    """raw_videos/ 下所有视频总数（含子目录）"""
    if not raw_dir.exists():
        return 0
    count = len([f for f in raw_dir.iterdir() if f.suffix.lower() in VIDEO_EXTS and not f.name.startswith(".")])
    for d in raw_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            count += len([f for f in d.iterdir() if f.suffix.lower() in VIDEO_EXTS])
    return count

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WORK_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.send_json(self.get_status())
            return
        if path == "/api/log":
            self.send_json({"log": self.get_recent_log()})
            return
        if path == "/api/dramas":
            raw_dir = WORK_DIR / "raw_videos"
            self.send_json({"dramas": _scan_dramas(raw_dir)})
            return
        if path == "/api/log-trailer":
            self.send_json({"log": self.get_recent_trailer_log()})
            return
        if path == "/api/config":
            self.send_json(self.get_config())
            return

        # 静态文件（根路径返回 index.html）
        elif path == "/" or path == "":
            self.serve_file("index.html")
        elif path.startswith("/static/"):
            self.serve_file(path.lstrip("/"))
        else:
            self.serve_file(path.lstrip("/"))
            return

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/run":
            self.handle_run()
        elif path == "/api/run-trailer":
            self.handle_run_trailer()
        elif path == "/api/open-folder":
            self.handle_open_folder()
        elif path == "/api/save-config":
            self.handle_save_config()
        elif path == "/api/viral-package":
            self.handle_viral_package()
        elif path == "/api/processing-result":
            self.handle_processing_result()
        elif path == "/api/warmup":
            self.handle_warmup()
        else:
            self.send_error(404)

    def serve_file(self, filename):
        filepath = WORK_DIR / filename
        if filepath.exists():
            ext = filepath.suffix
            mime = MIME_TYPES.get(ext, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def get_status(self):
        raw_dir = WORK_DIR / "raw_videos"
        bgm_dir = WORK_DIR / "bgm"
        out_dir = WORK_DIR / "output_videos"
        narr_dir = WORK_DIR / "narration"

        dramas = _scan_dramas(raw_dir)
        # 展示所有视频（含子目录）用于文件列表
        all_raw = []
        if dramas:
            for dr in dramas:
                p = Path(dr["path"])
                for f in p.iterdir():
                    if f.suffix.lower() in VIDEO_EXTS and not f.name.startswith("."):
                        prefix = f"{dr['name']}/" if dr["path"] != str(raw_dir) else ""
                        all_raw.append(f"{prefix}{f.name}")

        return {
            "dramas": dramas,
            "raw_videos": all_raw,
            "raw_count":  _total_video_count(raw_dir),
            "bgm_files":  _list_files(bgm_dir),
            "bgm_count":  len(_list_files(bgm_dir)),
            "outputs":    _list_files(out_dir),
            "output_count": len(_list_files(out_dir)),
            "narration_files": _list_files(narr_dir),
            "narration_count": len(_list_files(narr_dir)),
        }

    def get_recent_log(self):
        log_file = WORK_DIR / "processing.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                return "".join(lines[-100:])
            except Exception:
                return "[日志读取失败]"
        return ""

    def get_recent_trailer_log(self):
        log_file = WORK_DIR / "trailer_processing.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                return "".join(lines[-100:])
            except Exception:
                return "[日志读取失败]"
        return ""

    def handle_run(self):
        raw_dir = WORK_DIR / "raw_videos"
        dramas = _scan_dramas(raw_dir)

        if not dramas:
            self.send_json({"ok": False, "error": "raw_videos/ 中没有找到视频（支持子目录结构：raw_videos/剧名/*.mp4）"})
            return

        # 读取用户配置 + 已选剧目
        user_config = {}
        selected_dramas = None  # None = 全量
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            try:
                body = self.rfile.read(content_length)
                parsed = json.loads(body.decode("utf-8"))
                user_config = parsed
                selected_dramas = parsed.get("selected_dramas")
            except Exception:
                user_config = {}

        # 过滤只处理已选剧目
        if selected_dramas and len(selected_dramas) > 0:
            dramas = [d for d in dramas if d["name"] in selected_dramas]
            if not dramas:
                self.send_json({"ok": False, "error": f"未找到已选剧目: {selected_dramas}"})
                return

        # 保存用户配置供脚本读取
        config_file = WORK_DIR / "user_config.json"
        # 修复：只在有明确配置时才覆盖，否则保留现有配置
        if user_config and len(user_config) > 0:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(user_config, f, ensure_ascii=False, indent=2)
        else:
            # 请求体为空，保留现有配置
            # 注意：log 变量在此处未定义，改用 print（输出到 server.log）
            print(f"[{timestamp()}] ℹ️ 请求体为空，保留现有 user_config.json")

        total = sum(d["count"] for d in dramas)
        drama_names = ", ".join(d["name"] for d in dramas)
        sel_label = f"已选 {len(dramas)} 部" if selected_dramas else "全量"

        # 记录用户自定义的配置项
        customized = [k for k, v in user_config.items()
                      if v is not None and v != "" and v != "auto"] if user_config else []
        config_info = f"（自定义: {', '.join(customized[:3])}{'...' if len(customized)>3 else ''}）" if customized else "（全智能）"

        def run_processing():
            log_file = WORK_DIR / "processing.log"
            with open(log_file, "w", encoding="utf-8") as log:
                log.write(f"[{timestamp()}] 🎬 [{sel_label}] 处理 {len(dramas)} 部短剧（共{total}个视频）: {drama_names}\n")
                log.write(f"[{timestamp()}] ⚙️ 配置模式: {config_info}\n")
                log.flush()
                # shell=True + source venv 确保环境正确
                venv_act = str(WORK_DIR / '.venv' / 'bin' / 'activate')
                cmd_str = f". {venv_act} && python3 {str(WORK_DIR / 'ai_short_video_cutter_pro.py')} --config {str(config_file)}"
                proc = subprocess.Popen(
                    cmd_str, cwd=str(WORK_DIR), shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
                    log.write(line)
                    log.flush()
                proc.wait()
                log.write(f"\n[{timestamp()}] 处理完成，退出码: {proc.returncode}\n")

            # 读取最新发布的爆款发布包
            out_dir = WORK_DIR / "output_videos"
            viral_files = sorted(out_dir.glob("*_发布包.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            viral_package = None
            if viral_files:
                import json
                with open(viral_files[0], encoding="utf-8") as f:
                    viral_package = json.load(f)

            subprocess.run(["open", str(out_dir)])

            # 写入结果供轮询读取
            result_file = WORK_DIR / "processing_result.json"
            import json as json_mod
            with open(result_file, "w", encoding="utf-8") as rf:
                json_mod.dump({"done": True, "viral": viral_package, "exit_code": proc.returncode}, rf)

        t = threading.Thread(target=run_processing, daemon=True)
        t.start()
        self.send_json({"ok": True, "message": f"已启动，正在处理 {len(dramas)} 部短剧（{total}个视频）..."})

    def handle_run_trailer(self):
        """预告片生成接口"""
        raw_dir = WORK_DIR / "raw_videos"
        dramas = _scan_dramas(raw_dir)

        if not dramas:
            self.send_json({"ok": False, "error": "raw_videos/ 中没有找到视频"})
            return

        # 读取已选剧目
        selected_dramas = None
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            try:
                body = self.rfile.read(content_length)
                parsed = json.loads(body.decode("utf-8"))
                selected_dramas = parsed.get("selected_dramas")
            except Exception:
                pass

        if selected_dramas and len(selected_dramas) > 0:
            dramas = [d for d in dramas if d["name"] in selected_dramas]
            if not dramas:
                self.send_json({"ok": False, "error": "未找到已选剧目"})
                return

        total = sum(d["count"] for d in dramas)
        sel_label = f"已选 {len(dramas)} 部" if selected_dramas else "全量"

        def run_trailer():
            log_file = WORK_DIR / "trailer_processing.log"
            with open(log_file, "w", encoding="utf-8") as log:
                log.write(f"[{timestamp()}] 🎬 [{sel_label}] 生成预告片（{len(dramas)}部短剧）\n")
                log.flush()
                # shell=True + source venv
                venv_act = str(WORK_DIR / '.venv' / 'bin' / 'activate')
                cmd_str = f". {venv_act} && python3 {str(WORK_DIR / 'trailer_generator.py')}"
                proc = subprocess.Popen(
                    cmd_str, cwd=str(WORK_DIR), shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
                    log.write(line)
                    log.flush()
                proc.wait()
                log.write(f"\n[{timestamp()}] 预告片生成完成\n")
            subprocess.run(["open", str(WORK_DIR / "output_videos")])

        t = threading.Thread(target=run_trailer, daemon=True)
        t.start()
        self.send_json({"ok": True, "message": f"已启动预告片生成 [{sel_label}]（{len(dramas)}部）..."})

    def handle_open_folder(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        folder = qs.get("folder", [""])[0]
        folder_map = {
            "raw":   "raw_videos",
            "bgm":   "bgm",
            "output":"output_videos",
            "narration": "narration",
            "subtitles": "subtitles",
        }
        folder_name = folder_map.get(folder, "")
        if folder_name:
            subprocess.run(["open", str(WORK_DIR / folder_name)])
            self.send_json({"ok": True})
        else:
            self.send_json({"ok": False, "error": "未知文件夹"})

    def get_config(self):
        """读取配置"""
        config_file = WORK_DIR / "config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def handle_viral_package(self):
        """查询最新爆款发布包"""
        out_dir = WORK_DIR / "output_videos"
        viral_files = sorted(out_dir.glob("*_发布包.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if viral_files:
            with open(viral_files[0], encoding="utf-8") as f:
                self.send_json({"ok": True, "package": json.load(f), "file": str(viral_files[0].name)})
        else:
            self.send_json({"ok": False, "error": "暂无发布包，请先运行剪辑"})

    def handle_processing_result(self):
        """查询处理结果"""
        result_file = WORK_DIR / "processing_result.json"
        if result_file.exists():
            with open(result_file, encoding="utf-8") as f:
                self.send_json({"ok": True, **json.load(f)})
        else:
            self.send_json({"ok": False, "done": False})

    def handle_warmup(self):
        """预热接口：提前加载Whisper模型，消除首次处理延迟"""
        import time
        t0 = time.time()
        warmup_file = WORK_DIR / "warmup_done.txt"
        if warmup_file.exists():
            self.send_json({"ok": True, "warm": True, "msg": "Whisper模型已预热"})
            return

        def do_warmup():
            log_file = WORK_DIR / "processing.log"
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"\n[{timestamp()}] 🔥 开始预热Whisper模型...\n")
                log.flush()
                # shell=True + source venv
                venv_act = str(WORK_DIR / '.venv' / 'bin' / 'activate')
                py_cmd = (
                    "from faster_whisper import WhisperModel; "
                    "m=WhisperModel('small',device='cpu',compute_type='int8'); "
                    "open('warmup_done.txt','w').write('ok')"
                )
                cmd_str = f". {venv_act} && python3 -c \"{py_cmd}\""
                proc = subprocess.Popen(
                    cmd_str, cwd=str(WORK_DIR), shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True
                )
                for line in proc.stdout:
                    log.write(line)
                    log.flush()
                proc.wait()
                log.write(f"[{timestamp()}] ✅ 预热完成，耗时 {time.time()-t0:.0f}s\n")

        t = threading.Thread(target=do_warmup, daemon=True)
        t.start()
        self.send_json({"ok": True, "warm": False, "msg": f"预热已启动，预计75秒完成..."})

    def handle_save_config(self):
        """保存配置"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            config = json.loads(body.decode("utf-8"))
            config_file = WORK_DIR / "config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.send_json({"ok": True, "message": "配置已保存"})
        else:
            self.send_json({"ok": False, "error": "无配置数据"})



    def log_message(self, fmt, *args):
        pass

def timestamp():
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")

def main():
    os.chdir(WORK_DIR)
    print(f"\n{'='*50}")
    print(f"  🎬 短剧剪辑工作站 v2.0")
    print(f"  🌐 浏览器打开: http://localhost:{PORT}")
    print(f"  📁 工作目录: {WORK_DIR}")
    print(f"  按 Ctrl+C 停止服务")
    print(f"{'='*50}\n")
    webbrowser.open(f"http://localhost:{PORT}")

    # 多线程服务器：每个请求独立线程，避免视频处理阻塞其他请求
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        allow_reuse_address = True

    with ThreadedHTTPServer(("", PORT), Handler) as httpd:
        print(f"  ✅ 多线程模式已启用（每个请求独立线程）")
        print(f"  🔥 正在后台预热Ollama模型（约60秒）...")
        warmup_ollama()  # P1: 启动时预热Ollama，消除首次调用延迟
        httpd.serve_forever()


def warmup_ollama():
    """P1: 服务启动时预热Ollama模型，消除首次调用延迟"""
    import subprocess, time, logging
    logger = logging.getLogger("warmup")
    try:
        logger.info("🔥 预热Ollama模型 qwen3.5:4b...")
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate",
             "-H", "Content-Type: application/json",
             "-d", '{"model":"qwen3.5:4b","prompt":"hi","stream":false,"think":false}',
             "--max-time", "45"],
            capture_output=True, text=True, timeout=50
        )
        if result.returncode == 0:
            logger.info("✅ Ollama预热完成")
        else:
            logger.warning(f"⚠️ Ollama预热异常: {result.stderr}")
    except Exception as e:
        logger.warning(f"⚠️ Ollama预热失败: {e}")

if __name__ == "__main__":
    main()
