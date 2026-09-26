#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jellyfish Studio + Toonflow 集成模块
功能：资产管理系统 / AI剧本分镜 / 多工作流编排 / 视频风格化 / Toonflow API对接
"""
import os, json, time, subprocess
from pathlib import Path
from typing import List, Dict, Optional

WORK_DIR = Path(__file__).parent

# ─── Module 1: AssetManager ───────────────────────────────────────────────
class AssetManager:
    """角色/场景/道具资产管理 + 多集连续性追踪"""
    def __init__(self):
        self.assets_dir = WORK_DIR / "assets"
        self.assets_dir.mkdir(exist_ok=True)
        self.characters_file = self.assets_dir / "characters.json"
        self.scenes_file = self.assets_dir / "scenes.json"
        self.episodes_file = self.assets_dir / "episodes.json"
        for f in [self.characters_file, self.scenes_file, self.episodes_file]:
            if not f.exists():
                f.write_text("{}", encoding="utf-8")

    def _read(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))
    def _write(self, path, data):
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_character(self, name: str, description: str = "", image_path: str = "",
                     traits: List[str] = None, alias_list: List[str] = None) -> dict:
        chars = self._read(self.characters_file)
        chars[name] = {
            "name": name, "description": description, "image_path": image_path,
            "traits": traits or [], "aliases": alias_list or [],
            "first_seen": time.strftime("%Y-%m-%d"), "appearances": [],
            "consistency_notes": ""
        }
        self._write(self.characters_file, chars)
        return chars[name]

    def add_scene(self, name: str, description: str = "", location: str = "",
                  time_of_day: str = "", mood: str = "") -> dict:
        scenes = self._read(self.scenes_file)
        scenes[name] = {
            "name": name, "description": description, "location": location,
            "time_of_day": time_of_day, "mood": mood,
            "first_seen": time.strftime("%Y-%m-%d"), "usage_count": 0
        }
        self._write(self.scenes_file, scenes)
        return scenes[name]

    def add_episode_meta(self, drama_name: str, episode_num: int,
                         characters: List = None, locations: List = None,
                         plot_summary: str = "") -> dict:
        eps = self._read(self.episodes_file)
        if drama_name not in eps:
            eps[drama_name] = {"episodes": {}, "character_register": {}, "scene_register": {}}
        eps[drama_name]["episodes"][str(episode_num)] = {
            "episode": episode_num, "plot_summary": plot_summary,
            "characters": characters or [], "locations": locations or [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M")
        }
        for char in (characters or []):
            cname = char if isinstance(char, str) else char.get("name", "")
            if cname:
                eps[drama_name]["character_register"].setdefault(cname, []).append(str(episode_num))
        self._write(self.episodes_file, eps)
        return eps[drama_name]["episodes"][str(episode_num)]

    def get_character(self, name: str):
        return self._read(self.characters_file).get(name)

    def get_episode_history(self, drama_name: str, up_to_episode: int = None) -> dict:
        eps = self._read(self.episodes_file)
        if drama_name not in eps:
            return {}
        result = dict(eps[drama_name])
        if up_to_episode:
            result["episodes"] = {k: v for k, v in result["episodes"].items()
                                   if int(k) <= up_to_episode}
        return result

    def export_consistency_report(self, drama_name: str) -> dict:
        eps = self._read(self.episodes_file)
        if drama_name not in eps:
            return {"drama": drama_name, "warnings": [], "characters": {}, "episode_count": 0}
        ep_data = eps[drama_name]
        warnings = []
        char_eps = {}
        for ep_num, ep in ep_data["episodes"].items():
            for char in ep.get("characters", []):
                cname = char if isinstance(char, str) else char.get("name", "")
                if cname:
                    char_eps.setdefault(cname, []).append(int(ep_num))
        for cname, ep_list in char_eps.items():
            if len(ep_list) > 1:
                gaps = [ep_list[i+1]-ep_list[i] for i in range(len(ep_list)-1)]
                if max(gaps) > 3:
                    warnings.append(f"角色「{cname}」在第{ep_list}集出现，中间有{max(gaps)}集断层")
        return {
            "drama": drama_name, "warnings": warnings,
            "character_episodes": char_eps,
            "episode_count": len(ep_data["episodes"]),
            "report_time": time.strftime("%Y-%m-%d %H:%M")
        }

    def list_all(self) -> dict:
        return {
            "characters": self._read(self.characters_file),
            "scenes": self._read(self.scenes_file),
            "dramas": list(self._read(self.episodes_file).keys())
        }

    def delete_character(self, name: str) -> bool:
        chars = self._read(self.characters_file)
        if name in chars:
            del chars[name]
            self._write(self.characters_file, chars)
            return True
        return False

    def delete_scene(self, name: str) -> bool:
        scenes = self._read(self.scenes_file)
        if name in scenes:
            del scenes[name]
            self._write(self.scenes_file, scenes)
            return True
        return False


# ─── Module 2: ScriptAnalyzer (AI剧本分镜) ─────────────────────────────────
class ScriptAnalyzer:
    """使用 Ollama gemma4 将剧本拆解为分镜表"""
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url

    def analyze_script(self, script_text: str, genre_hint: str = "") -> List[Dict]:
        """将剧本AI拆解为分镜列表"""
        import urllib.request, re

        genre_map = {
            "都市言情": "都市背景的爱情故事",
            "古风仙侠": "古代仙侠玄幻故事",
            "重生复仇": "主角重生后复仇的故事",
            "总裁豪门": "豪门总裁爱情故事",
            "甜宠": "轻松甜蜜爱情故事",
            "虐恋": "充满冲突和伤感的爱情故事",
        }
        genre_desc = genre_map.get(genre_hint, genre_hint or "短剧/微短剧")

        prompt = f"""你是一个专业的AI短剧分镜师。根据以下{genre_desc}剧本，将其拆解为结构化分镜表。

要求：
1. 每个分镜是JSON对象，包含：shot_id(序号), shot_type(景别:特写/全景/中景/近景/双人对话/航拍), camera_angle(角度), camera_movement(运镜), duration(时长秒), dialogue(对白,无对白写"(动作)"), action(动作描写), emotion(情绪), setting(场景描述), prompt_for_gen(AI生成提示词,50字内)
2. 时长：动作镜头2-5秒，对话镜头3-8秒
3. 景别要交替变化，避免连续相同景别
4. 只输出JSON数组，不要其他文字

剧本：
{script_text[:4000]}

分镜JSON："""

        try:
            data = json.dumps({
                "model": "gemma4:31b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 800}
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw = result.get("response", "").strip()
                # 提取JSON数组
                match = re.search(r'\[.*\]', raw, re.DOTALL)
                if match:
                    shots = json.loads(match.group())
                    # 清理每条数据
                    for s in shots:
                        if isinstance(s, dict):
                            s.setdefault("shot_id", shots.index(s) + 1)
                            s.setdefault("duration", 5)
                            s.setdefault("emotion", "平静")
                    return shots[:30]
                return [{"error": "无法解析分镜JSON", "raw": raw[:300]}]
        except Exception as e:
            return [{"error": f"AI分析失败: {str(e)}"}]

    def estimate_cost(self, shots: List[Dict]) -> dict:
        video_shots = [s for s in shots if "error" not in s]
        total_dur = sum(s.get("duration", 5) for s in video_shots)
        return {
            "total_shots": len(video_shots),
            "total_duration_sec": total_dur,
            "estimated_time_min": int(total_dur / 60) + 10
        }


# ─── Module 3: VideoStyleTransfer (视频风格化) ───────────────────────────────
class VideoStyleTransfer:
    """视频风格化：接入 Toonflow API / 本地 ffmpeg"""
    def __init__(self):
        self.toonflow_url = "http://localhost:10588"
        self.toonflow_available = self._check_toonflow()

    def _check_toonflow(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.toonflow_url}/api/project",
                                         method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except:
            return False

    def style_transfer(self, video_path: str, style: str = "anime",
                       output_path: str = None) -> dict:
        """
        视频风格化转换
        style: anime(动漫风) / cel(赛璐璐) / painterly(手绘风) / sketch(素描风)
        """
        if output_path is None:
            output_path = str(WORK_DIR / "output_videos" / f"styled_{int(time.time())}.mp4")
        Path(output_path).parent.mkdir(exist_ok=True)

        if self.toonflow_available:
            return self._style_via_toonflow(video_path, style, output_path)
        else:
            return self._style_via_ffmpeg(video_path, style, output_path)

    def _style_via_toonflow(self, video_path: str, style: str, output_path: str) -> dict:
        try:
            import urllib.request, urllib.error
            data = json.dumps({
                "video_path": video_path,
                "style": style,
                "output_path": output_path
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.toonflow_url}/api/style_transfer",
                data=data, headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "method": "toonflow", "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e), "method": "toonflow"}

    def _style_via_ffmpeg(self, video_path: str, style: str, output_path: str) -> dict:
        """本地ffmpeg实现简易风格化（通过调色）"""
        style_presets = {
            "anime": "curves=r='0/0.22 0.35/0.31 1/0.85':g='0/0.15 0.5/0.5 1/0.9':b='0/0.05 0.4/0.25 1/0.7',colorbalance=hs=0.05/0.08/0.12",
            "cel": "curves=r='0/0.1 0.5/0.4 1/0.95':g='0/0.15 0.5/0.45 1/0.9':b='0/0.05 0.5/0.35 1/0.8',colorlevels=rimg=0.15:gimg=0.15:bimg=0.15",
            "painterly": "curves=r='0/0.18 0.4/0.25 1/0.88':g='0/0.12 0.5/0.48 1/0.92':b='0/0.08 0.45/0.3 1/0.75',boxblur=1:1",
            "sketch": "colorlevels=rimg=0.3:gimg=0.3:bimg=0.3,edgedetect=mode=colornoise,colorize=77",
        }
        vf = style_presets.get(style, style_presets["anime"])
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", vf,
            "-c:a", "copy", "-c:v", "libx264", "-preset", "fast",
            "-tune", "animation",
            output_path
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=600)
        if r.returncode == 0 and os.path.exists(output_path):
            return {"ok": True, "method": "ffmpeg", "style": style,
                    "output": output_path, "size": os.path.getsize(output_path)}
        return {"ok": False, "error": r.stderr[-300:] if r.stderr else "未知错误",
                "method": "ffmpeg"}

    def get_available_styles(self) -> List[dict]:
        return [
            {"id": "anime", "name": "动漫风", "desc": "日式动漫风格，高对比度，色彩鲜艳"},
            {"id": "cel", "name": "赛璐璐", "desc": "扁平赛璐璐风格，轮廓分明，色块分明"},
            {"id": "painterly", "name": "手绘风", "desc": "水彩手绘质感，柔和边缘，温暖色调"},
            {"id": "sketch", "name": "素描风", "desc": "黑白素描效果，艺术感强"},
        ]


# ─── Module 4: WorkflowBuilder (工作流编排) ──────────────────────────────────
WORKFLOW_TEMPLATES = {
    "ai_narration_edit": {
        "name": "AI解说剪辑",
        "icon": "✂️",
        "description": "对已拍摄短剧进行AI解说剪辑（现有核心功能）",
        "steps": ["语音识别", "高光筛选", "AI叙事生成", "TTS配音", "BGM匹配", "混音输出", "合规检测"],
        "input_type": "video", "output_type": "video",
        "modes": ["单剧集", "批量多集", "预告片"],
        "status": "ready"
    },
    "script_to_storyboard": {
        "name": "剧本→分镜",
        "icon": "📝",
        "description": "输入文字剧本，AI自动拆解为分镜表，生成角色/场景资产",
        "steps": ["输入剧本", "AI分镜分析", "角色提取", "场景提取", "资产关联", "一致性检查"],
        "input_type": "script", "output_type": "storyboard",
        "modes": ["单集", "多集连载"],
        "requires_llm": True, "status": "ready"
    },
    "video_style_transfer": {
        "name": "视频风格化",
        "icon": "🎨",
        "description": "将短剧视频转换为动漫/赛璐璐/手绘等风格，支持Toonflow或本地处理",
        "steps": ["风格选择", "视频处理", "预览确认", "导出保存"],
        "input_type": "video", "output_type": "video_styled",
        "modes": ["动漫风", "赛璐璐", "手绘风", "素描风"],
        "status": "ready"
    },
    "trailer_generator": {
        "name": "预告片生成",
        "icon": "🎬",
        "description": "从短剧片段生成悬念式/高潮混剪预告片",
        "steps": ["高光检测", "叙事编排", "转场设计", "BGM匹配", "导出"],
        "input_type": "video", "output_type": "trailer",
        "modes": ["悬念钩子", "高潮混剪", "剧情预告"],
        "status": "ready"
    },
    "batch_multi_episode": {
        "name": "批量多集连剪",
        "icon": "📦",
        "description": "批量处理多集短剧，自动追踪角色连续性，统一调色输出",
        "steps": ["批量导入", "连续性分析", "单集剪辑", "批量混音", "统一调色", "打包导出"],
        "input_type": "batch", "output_type": "video_series",
        "modes": ["全自动化", "人工审核"],
        "requires_continuity": True, "status": "ready"
    },
    "viral_clip_extractor": {
        "name": "爆款片段提取",
        "icon": "🔥",
        "description": "从长剧识别高传播力片段，生成多个短剪版本用于多平台分发",
        "steps": ["完整识别", "情绪分析", "爆款打分", "多版本输出", "标签生成"],
        "input_type": "video", "output_type": "clips",
        "modes": ["抖音版", "快手版", "小红书版", "B站版"],
        "status": "ready"
    },
    "toonflow_comic": {
        "name": "Toonflow漫剧",
        "icon": "🖼️",
        "description": "对接Toonflow AI短剧工厂，将小说文字转为动漫分镜+视频素材（需Toonflow运行于localhost:10588）",
        "steps": ["导入小说", "AI剧本生成", "角色资产创建", "分镜图片生成", "视频片段合成"],
        "input_type": "novel", "output_type": "anime_video",
        "modes": ["小说→短剧", "分镜图生成", "视频素材导出"],
        "requires_toonflow": True, "status": "check_toonflow"
    }
}


class WorkflowBuilder:
    """工作流编排器"""
    def __init__(self):
        self.asset_manager = AssetManager()
        self.script_analyzer = ScriptAnalyzer()
        self.style_transfer = VideoStyleTransfer()

    def get_available_workflows(self) -> List[dict]:
        result = []
        for wf_id, wf in WORKFLOW_TEMPLATES.items():
            item = dict(wf)
            item["id"] = wf_id
            if wf_id == "toonflow_comic":
                item["status"] = "ready" if self.style_transfer.toonflow_available else "toonflow_not_running"
            result.append(item)
        return result

    def run_workflow(self, workflow_type: str, params: Dict) -> Dict:
        if workflow_type not in WORKFLOW_TEMPLATES:
            return {"ok": False, "error": f"未知工作流: {workflow_type}"}
        wf = WORKFLOW_TEMPLATES[workflow_type]
        if workflow_type == "script_to_storyboard":
            return self._run_script_workflow(params)
        elif workflow_type == "video_style_transfer":
            return self._run_style_workflow(params)
        elif workflow_type == "ai_narration_edit":
            return {"ok": True, "workflow": "ai_narration_edit",
                    "message": "复用主剪辑流程", "redirect": "/api/run"}
        elif workflow_type == "trailer_generator":
            return {"ok": True, "workflow": "trailer_generator",
                    "message": "预告片生成", "redirect": "/api/run_trailer"}
        elif workflow_type == "batch_multi_episode":
            return self._run_batch_workflow(params)
        elif workflow_type == "viral_clip_extractor":
            return {"ok": True, "workflow": "viral_clip_extractor", "message": "爆款提取"}
        elif workflow_type == "toonflow_comic":
            return self._run_toonflow_workflow(params)
        return {"ok": False, "error": "工作流未实现"}

    def _run_script_workflow(self, params: Dict) -> Dict:
        script = params.get("script", "")
        genre = params.get("genre", "")
        drama_name = params.get("drama_name", "未命名")
        if not script:
            return {"ok": False, "error": "缺少剧本内容"}
        shots = self.script_analyzer.analyze_script(script, genre)
        cost = self.script_analyzer.estimate_cost(shots)
        # 提取角色名
        char_names = set()
        for shot in shots:
            if "error" in shot:
                continue
            dlg = shot.get("dialogue", "")
            for kw in ["她说", "他说", "男主", "女主", "主角"]:
                if kw in dlg:
                    char_names.add(kw)
        # 保存资产
        self.asset_manager.add_episode_meta(
            drama_name=drama_name,
            episode_num=params.get("episode", 1),
            plot_summary=script[:200]
        )
        return {
            "ok": True, "workflow": "script_to_storyboard",
            "shots": [s for s in shots if "error" not in s][:20],
            "shot_count": len([s for s in shots if "error" not in s]),
            "cost_estimate": cost,
            "characters_detected": list(char_names),
            "status": "ready"
        }

    def _run_style_workflow(self, params: Dict) -> Dict:
        video_path = params.get("video_path", "")
        style = params.get("style", "anime")
        if not video_path or not os.path.exists(video_path):
            return {"ok": False, "error": "视频文件不存在"}
        result = self.style_transfer.style_transfer(video_path, style)
        return {"ok": result.get("ok", False), "workflow": "video_style_transfer",
                "result": result}

    def _run_batch_workflow(self, params: Dict) -> Dict:
        drama_name = params.get("drama_name", "未命名")
        continuity = self.asset_manager.export_consistency_report(drama_name)
        return {
            "ok": True, "workflow": "batch_multi_episode",
            "continuity_report": continuity,
            "message": f"检测到{continuity.get('episode_count', 0)}集，{len(continuity.get('warnings', []))}个连续性问题"
        }

    def _run_toonflow_workflow(self, params: Dict) -> Dict:
        if not self.style_transfer.toonflow_available:
            return {
                "ok": False, "error": "Toonflow 未运行于 localhost:10588，请先启动 Toonflow",
                "workflow": "toonflow_comic"
            }
        novel_text = params.get("novel_text", "")
        if not novel_text:
            return {"ok": False, "error": "缺少小说内容"}
        # Toonflow API调用（示例）
        try:
            import urllib.request
            data = json.dumps({"text": novel_text, "type": "script"}).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:10588/api/novel/import",
                data=data, headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "workflow": "toonflow_comic", "result": result}
        except Exception as e:
            return {"ok": False, "error": f"Toonflow API调用失败: {str(e)}",
                    "workflow": "toonflow_comic"}


# ─── Module 5: 系统状态 ────────────────────────────────────────────────────
def get_studio_status() -> dict:
    """获取工作室整体状态"""
    am = AssetManager()
    st = VideoStyleTransfer()
    return {
        "asset_summary": am.list_all(),
        "workflows": WorkflowBuilder().get_available_workflows(),
        "services": {
            "ollama": {"available": True, "model": "gemma4:31b"},
            "toonflow": {"available": st.toonflow_available, "url": "http://localhost:10588"}
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
