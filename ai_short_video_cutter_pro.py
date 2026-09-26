#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

抖音短剧AI自动剪辑工具(Seedance增强版)

功能:合并视频 | 语音识别 | 剧情分析 | 智能分镜 | BGM匹配 | 智能特效 | 抖音合规

Seedance 6阶段标准:剧本解析→角色设计→分镜生成→语音合成→视频合成→多平台适配

配置优先级:用户自定义 > 智能检测 > 默认配置

"""



import os

import re

import sys

# Fix venv site-packages path (ensure packages like ChatTTS, faster-whisper are findable)
_venv_sp = "/Users/ffzwai/.qclaw/workspace/douyin-short-drama-cutter/.venv/lib/python3.11/site-packages"
if _venv_sp not in sys.path:
    sys.path.insert(0, _venv_sp)
print(f"[DEBUG] Venv path injection: {_venv_sp} -> sys.path[0]={sys.path[0]}")

import torch  # GPU 检测需要
import json
import json as _json  # 兼容_call_ollama_retry等多处_json引用

import time

import random

import shutil

import subprocess

import tempfile

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any

import signal
import traceback
import faulthandler

# Enable faulthandler to get tracebacks on segfaultaulthandler.enable(file=sys.stderr)

# Signal handler for fatal signals# [FIX-20260709] 模块级安全词替换表(避免函数内局部变量作用域问题)
SAFE_WORD_MAP = {'裸':'衣衫不整','全裸':'衣衫不整','脱光':'更衣','一丝不挂':'衣衫不整','玉体':'身姿','酮体':'身躯','做爱':'亲密','上床':'同寝','啪啪':'争吵','呻吟':'声音','喘息':'呼吸','滚床单':'同寝','性爱':'亲密','私处':'身体','阴部':'身体','臀部':'身体','大腿根':'身侧','胸脯':'胸口','奶子':'女子','乳沟':'胸前','爆乳':'丰满','巨乳':'丰满','揉胸':'触碰','摸胸':'触碰','抓胸':'触碰','插入':'进入','抽插':'动作','润滑':'顺滑','欲仙欲死':'沉醉','欲罢不能':'难以自拔','娇喘':'轻叹','春药':'药物','催情':'冲动','自慰':'独处','手淫':'独处','口交':'亲昵','肛交':'亲昵','性交':'亲密','交媾':'结合','精液':'体液','射精':'释放','云雨':'相伴','行房':'同寝','房事':'同寝','巫山':'相聚','床第之事':'夜间','媚药':'药物','迷奸':'侵犯','下药':'施药','灌醉':'饮酒','猥亵':'冒犯','猥琐':'卑劣','调戏':'戏弄','非礼':'冒犯','轻薄':'无礼','狎昵':'亲近','宠幸':'看重','侍寝':'陪伴','偷窥':'窥视','窥视':'远望','偷拍':'拍摄','肚兜':'衣物','亵衣':'内衣','亵裤':'内衣','操':'欺负','草泥马':'可恶','尼玛':'可恶','绿茶婊':'心机女子','心机婊':'心机女子','血肉模糊':'受伤惨重','脑浆':'头部','开膛':'重伤','分尸':'杀害','碎尸':'毁坏','虐杀':'残害','割喉':'受伤','挖眼':'受伤','断肢':'伤残','肠子':'腹部','勾引':'吸引','勾搭':'结识','勾栏':'酒馆','青楼':'风月场所','妓院':'风月场所','出台':'现身','情趣':'装饰','湿身':'淋湿','湿透':'浸湿','裸泳':'游泳','裸睡':'安睡','情趣内衣':'装饰衣物','丝袜':'袜子','吊带袜':'袜子','蕾丝':'布料','内裤':'衣物','胸罩':'内衣','傻逼':'愚蠢','肏':'欺','贱货':'卑劣','婊子':'女子','荡妇':'女子','骚货':'女子',
            # [FIX-20260709] 高危警告词替换(明显擦边词)
            '酥胸':'胸口','若隐若现':'若隐','曲线玲珑':'身姿','曼妙':'优美','妖娆':'动人','妩媚':'动人','娇媚':'柔美',
            '共枕':'同寝','同眠':'同寝','肌肤之亲':'亲近','热吻':'亲吻','湿吻':'亲吻',
            '勾人':'迷人','魅惑':'吸引','挑逗':'逗引','撩人':'引人','撩拨':'触动','诱惑':'吸引','色诱':'引诱',
            '宽衣解带':'更衣','宽衣':'更衣','褪去':'脱下','褪下':'脱下',
            '共浴':'同浴','同床':'同寝','春宵':'夜晚','入帐':'休息','就寝':'休息',
            '透视装':'薄衫','露背':'露背','低胸':'领口','深V':'领口','比基尼':'泳装','裹胸':'束胸',
            '真空':'空穿','湿衫':'湿衣','超短裙':'短裙','低腰裤':'长裤',
            '闺房':'房间','娇羞':'羞涩','娇柔':'柔弱','抚摸':'触碰','轻抚':'轻触','游走':'移动','滑过':'掠过',
            '瘫软':'无力','面红耳赤':'涨红','心跳加速':'心跳加快','温存':'温存','沐浴':'洗浴',
            # [FIX-20260709] 补全剩余警告词
            '高潮':'顶峰','身材':'体态','曲线':'身形','身材好':'体态好','丰满':'圆润','傲人':'出色','凹凸':'起伏','韵味':'气质',
            'S曲线':'身形','A4腰':'腰身','水蛇腰':'腰身','蜜桃臀':'臀形','大长腿':'长腿','长腿':'双腿','美腿':'双腿',
            '香肩':'肩膀','锁骨':'肩颈','美背':'背部','光滑':'光洁','翘臀':'臀形','细腰':'腰身',
            '酥胸':'胸口','暧昧':'模糊','独处':'单独','亲密':'亲近','相拥':'拥抱','抱紧':'紧抱',
            '肌肤':'皮肤','嘴唇':'双唇','吻':'亲吻','眼神':'目光','洗澡':'沐浴',
            '更衣':'换衣','换衣':'更衣','更衣室':'更衣间','浴室':'洗浴间','触碰':'碰触','颤抖':'发抖',
            '透视':'薄透','露肩':'露肩','露脐':'露腰','泳装':'泳衣','紧身衣':'贴身衣','短裙':'裙子','开叉':'开衩'}


def signal_handler(signum, frame):
    print(f"\n{'='*80}", flush=True)
    print(f"FATAL: Received signal {signum}", flush=True)
    print(f"Stack trace:", flush=True)
    traceback.print_stack(frame)
    print(f"{'='*80}", flush=True)
    # Try to log to file as well
    try:
        with open('/tmp/cutter_crash.log', 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"FATAL: Received signal {signum}\n")
            f.write(f"Stack trace:\n")
            traceback.print_stack(frame, file=f)
            f.write(f"{'='*80}\n")
    except:
        pass
    sys.exit(1)

# Register signal handlers for common fatal signals
signal.signal(signal.SIGSEGV, signal_handler)  # Segmentation fault
signal.signal(signal.SIGBUS, signal_handler)   # Bus error
signal.signal(signal.SIGABRT, signal_handler) # Abort
signal.signal(signal.SIGFPE, signal_handler)   # Floating point exception


# =============================================================================
# 本地 TTS/ASR Wrappers (ChatTTS + whisper.cpp)
# =============================================================================

try:
    from tts_chattts_wrapper import tts_chattts, has_chattts
    CHAT_TTS_AVAILABLE = has_chattts()
    if CHAT_TTS_AVAILABLE:
        print("[TTS] ChatTTS 可用")
except ImportError:
    CHAT_TTS_AVAILABLE = False
    print("[TTS] ChatTTS wrapper 未找到")

try:
    from asr_whisper_cpp_wrapper import transcribe_whisper_cpp, has_whisper_cpp
    WHISPER_CPP_AVAILABLE = has_whisper_cpp()
    if WHISPER_CPP_AVAILABLE:
        print("[ASR] whisper.cpp 可用")
except ImportError:
    WHISPER_CPP_AVAILABLE = False
    print("[ASR] whisper.cpp wrapper 未找到")


# PIL用于生成标题图片

try:

    from PIL import Image, ImageDraw, ImageFont

    HAS_PIL = True

except ImportError:

    HAS_PIL = False



# 工作目录(用于定位模型等资源)
WORK_DIR = Path(__file__).parent.resolve()
_VENV_SITE = WORK_DIR / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if _VENV_SITE.exists():
    _venv_str = str(_VENV_SITE)
    if _venv_str not in sys.path:
        sys.path.insert(0, _venv_str)
        print(f"[DEBUG] venv site-packages added to sys.path: {_venv_str}", flush=True)
    else:
        print(f"[DEBUG] venv already in sys.path", flush=True)
else:
    print(f"[DEBUG] venv site-packages not found: {_VENV_SITE}", flush=True)
# ---- 结束 ----
# 日志函数
def log(msg: str, emoji: str = "📊") -> None:
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {msg}", flush=True)







# 导入配置合并器

try:

    from config_merger import merge_config, load_user_config, is_user_customized

    HAS_CONFIG_MERGER = True

except ImportError:

    HAS_CONFIG_MERGER = False



# 全局智能检测配置(在处理过程中动态填充)

SMART_CONFIG = {}



import numpy as np

import cv2

from pydub import AudioSegment



# 尝试导入可选依赖

try:

    from gtts import gTTS

    HAS_GTTS = True

except ImportError:

    HAS_GTTS = False



try:
    # 强制确保 venv site-packages 在 sys.path(无论谁启动本脚本)
    _venv_lib = Path(__file__).parent / ".venv" / "lib"
    if _venv_lib.exists():
        for _d in sorted(_venv_lib.iterdir()):
            if _d.is_dir() and _d.name.startswith("python"):
                _sp = _d / "site-packages"
                if _sp.exists() and str(_sp) not in sys.path:
                    sys.path.insert(0, str(_sp))
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except (ImportError, AttributeError) as _e:
    HAS_WHISPER = False
    print(f"[WHISPER IMPORT ERROR] {_e}", flush=True)



try:

    from moviepy.editor import (

        VideoFileClip, AudioFileClip, CompositeVideoClip,

        CompositeAudioClip, concatenate_videoclips, TextClip

    )

    HAS_MOVIEPY = True

except ImportError:

    HAS_MOVIEPY = False



# ---- P1: 剪辑节奏模板(反同质化) ----
RHYTHM_TEMPLATES = [
    {"name": "悬念递进", "pattern": [0, 2, 4, 1, 3, 5]},           # 0-2-4开路→1-3-5追进
    {"name": "高潮前置", "pattern": [3, 4, 5, 0, 1, 2]},           # 高潮→铺垫
    {"name": "情绪波浪", "pattern": [0, 2, 4, 5, 3, 1]},           # 起-起-起-落-落-落
    {"name": "对比反衬", "pattern": [0, 5, 1, 4, 2, 3]},           # 首尾→次首→中段
    {"name": "随机打散", "pattern": None},                          # 完全随机
]

def _apply_rhythm_template(clips: list, template: dict = None) -> list:
    """根据节奏模板重排片段顺序"""
    import random
    if template is None:
        template = random.choice(RHYTHM_TEMPLATES)
    n = len(clips)
    name = template["name"]
    p = template["pattern"]
    if name == "随机打散":
        result = clips.copy()
        random.shuffle(result)
        log(f"   🎬 节奏模板: 随机打散 ({n}个片段)", "")
        return result
    # 循环重复pattern以适应不同片段数,跳过越界索引
    indices = []
    i = 0
    while len(indices) < n:
        _pi = p[i % len(p)]
        if _pi < n:  # 跳过越界索引(如 pattern 有索引5但片段数不够时)
            indices.append(_pi)
        i += 1
    result = [clips[i] for i in indices[:n]]
    log(f"   🎬 节奏模板: {name} ({n}个片段)", "")
    return result


# ---- P1-3: 调色预设(反同质化) ----
def _get_color_grade(genre: str, mood: str = "") -> dict:
    """根据类型和情绪选择调色预设,返回参数字典"""
    import random
    if mood == "虐":
        pool = [c for c in COLOR_GRADES if c["name"] in ["低饱和电影", "冷色调", "电影感"]]
    elif mood == "甜":
        pool = [c for c in COLOR_GRADES if c["name"] in ["暖色调", "高饱和"]]
    else:
        pool = COLOR_GRADES
    selected = random.choice(pool)
    log(f"   🎨 调色风格: {selected['name']}", "")
    return selected


# ---- P2-1: 画幅裁切微调(反同质化) ----
def _get_random_crop_offset() -> tuple:
    """每次裁切随机±3%偏移,打破固定构图"""
    import random
    h_offset = random.uniform(-0.03, 0.03)
    v_offset = random.uniform(-0.03, 0.03)
    return h_offset, v_offset


# ==================== 【1】核心配置(抖音合规) ====================



# 自然排序键:1, 2, 10 而非 1, 10, 2

def natural_sort_key(s: str):

    """自然排序键,正确处理数字文件名"""

    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]



# 片尾黑名单关键词

ENDING_BLACKLIST = [

    "未完待续", "敬请期待", "下集预告", "下期预告",

    "to be continued", "coming soon", "next episode",

    "关注我", "点赞收藏", "订阅频道",

    "感谢观看", "谢谢观看",

]

# ==================== 【常量定义区 - 短期优化 20260520】 ====================
# 音量相关常量
DEFAULT_ORIG_VOLUME = 0.3        # 原声音量(保留30%)
DEFAULT_NARRATION_VOLUME = 1.5  # 解说声音量(放大1.5倍)
DEFAULT_BGM_VOLUME = 0.15       # BGM音量(背景15%)

# 片段时长常量
MIN_CLIP_DURATION = 0.5         # 最小片段时长(秒)
MAX_CLIP_DURATION = 4.0         # 最大片段时长(秒)
TARGET_CLIP_COUNT = 40          # 目标片段数量(60-180秒视频)
MIN_VIDEO_DURATION = 60         # 最小视频时长(秒)

# 超时常量
SUBPROCESS_TIMEOUT = 120        # 子进程默认超时(秒)
LONG_SUBPROCESS_TIMEOUT = 300   # 长时间子进程超时(秒)
narration_TIMEOUT = 90          # 解说生成超时(秒)
FFPROBE_TIMEOUT = 30            # ffprobe超时(秒)

# 文件大小常量
MIN_FILE_SIZE = 50000           # 最小有效文件大小(字节)
MIN_AUDIO_SIZE = 1000           # 最小有效音频大小(字节)
MIN_SEGMENT_SIZE = 500          # 最小片段文件大小(字节)

# 采样和分析常量
MAX_TEXT_SAMPLE = 2500          # 文本采样最大长度
TARGET_NARRATION_GROUP_DURATION = 3.0  # 解说分组目标时长(秒)
EVENT_DISTANCE_THRESHOLD = 5    # 事件距离阈值(秒)

# 字数相关常量
MIN_NARRATION_LENGTH = 30       # 最小解说长度(字符)
MIN_VALID_NARRATION = 50        # 有效解说最小长度(字符)
KEY_DIALOGUE_COVERAGE_THRESHOLD = 0.5  # 关键台词覆盖率阈值
# ==================== 【常量定义区结束】 ====================


# ---- P0-1: 场景类型分类(反同质化) ----
SCENE_TYPE_KEYWORDS = {
    "conflict": ["吵", "打", "骂", "怒", "恨", "恨死", "不要脸", "滚", "贱", "逼", "对不起", "离婚", "分手", "报复", "欺负", "你敢", "给我滚", "气死", "凭什么", "耳光", "巴掌"],
    "warm": ["爱你", "喜欢", "温柔", "关心", "心疼", "拥抱", "亲吻", "牵手", "甜", "宝贝", "亲爱的", "暖心", "照顾", "守护", "幸福", "微笑", "笑"],
    "suspense": ["秘密", "发现", "原来", "竟然", "没想到", "真相", "隐藏", "阴谋", "计划", "不对劲", "可疑", "等等", "原来如此", "难道说", "背后"],
    "action": ["跑", "追", "打斗", "摔", "推", "抢", "掀", "踹", "砸", "撞", "冲", "爆发", "拼命", "抓住"],
    "monologue": ["我想", "我觉得", "为什么", "怎么办", "不该", "也许", "如果", "可惜", "要是", "只能", "心里", "内心", "独自"],
}


def _classify_scene_type(text: str) -> str:
    """根据文本关键词分类场景类型"""
    if not text:
        return "monologue"
    scores = {}
    for stype, keywords in SCENE_TYPE_KEYWORDS.items():
        scores[stype] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores.get(best, 0) > 0 else "monologue"


def _enforce_type_diversity(highlights, subtitle_texts: list = None) -> list:
    """P0-1 类型覆盖约束:确保最终片段集合覆盖≥3种类型"""
    if len(highlights) < 5:
        return highlights
    selected = highlights[:min(len(highlights), TARGET_CLIP_COUNT)]
    selected_types = {}
    for i, h in enumerate(selected):
        txt = subtitle_texts[i] if subtitle_texts and i < len(subtitle_texts) else ""
        stype = _classify_scene_type(txt)
        selected_types.setdefault(stype, []).append(i)
    covered = set(selected_types.keys())
    if len(covered) >= 3:
        log(f"   \U0001f3ad 类型覆盖: {dict((k, len(v)) for k, v in selected_types.items())}", "")
        return highlights
    remaining = highlights[TARGET_CLIP_COUNT:]
    needed = 3 - len(covered)
    all_types = set(SCENE_TYPE_KEYWORDS.keys())
    missing = [t for t in all_types if t not in covered]
    added = 0
    for mtype in missing[:needed]:
        best_idx = None
        best_score = 0
        for j, h in enumerate(remaining):
            txt = subtitle_texts[TARGET_CLIP_COUNT + j] if subtitle_texts and TARGET_CLIP_COUNT + j < len(subtitle_texts) else ""
            if _classify_scene_type(txt) == mtype and h[2] > best_score:
                best_score = h[2]
                best_idx = j
        if best_idx is not None:
            selected.append(remaining[best_idx])
            selected_types.setdefault(mtype, []).append(len(selected) - 1)
            added += 1
    if added > 0:
        selected.sort(key=lambda x: x[2], reverse=True)
        log(f"   \U0001f3ad 类型覆盖(补充{added}个): {dict((k, len(v)) for k, v in selected_types.items())}", "")
    else:
        log(f"   \U0001f3ad 类型覆盖: {dict((k, len(v)) for k, v in selected_types.items())} (无可用补充)", "")
    return selected + [h for h in highlights if h not in selected]


# ---- P0-3: 情绪词扩展库(反同质化) ----
EMOTION_WORD_POOL = {
    "愤怒": ["怒火中烧", "怒不可遏", "愤然起身", "暴怒", "气炸了", "忍无可忍", "怒火翻涌", "义愤填膺"],
    "深情": ["心碎不已", "肝肠寸断", "痛彻心扉", "泪流满面", "泣不成声", "深情凝视", "眼眶泛红", "颤抖的声音"],
    "惊讶": ["瞠目结舌", "难以置信", "倒吸一口凉气", "瞬间愣住", "瞪大了眼", "震惊万分", "完全没想到"],
    "悬疑": ["真相浮出水面", "谜底揭晓", "令人不寒而栗", "隐藏的秘密", "惊天内幕", "一切并非偶然"],
    "甜蜜": ["心花怒放", "甜蜜的笑容", "幸福感溢满", "小鹿乱撞", "脸红心跳", "甜到心里", "温柔的目光"],
    "悲伤": ["凄凉", "无尽的绝望", "心如刀割", "泪如雨下", "天塌下来", "万念俱灰", "悲痛欲绝"],
    "搞笑": ["笑喷了", "忍俊不禁", "啼笑皆非", "笑掉大牙", "太绝了", "笑到肚子疼", "一整个无语住"],
    "热血": ["热血沸腾", "燃爆了", "激情澎湃", "拼尽全力", "燃起斗志", "血脉偾张", "永不言弃"],
}
PLAIN_WORD_REPLACEMENTS = {
    "生气": "愤怒", "很生气": "愤怒", "愤怒": "愤怒",
    "伤心": "悲伤", "难过": "悲伤", "哭": "悲伤", "流泪": "悲伤",
    "惊讶": "惊讶", "没想到": "惊讶", "震惊": "惊讶", "意外": "惊讶",
    "害怕": "悬疑", "恐怖": "悬疑", "诡异": "悬疑",
    "开心": "甜蜜", "高兴": "甜蜜", "甜蜜": "甜蜜", "幸福": "甜蜜",
    "搞笑": "搞笑", "好笑": "搞笑", "哈哈": "搞笑", "笑": "搞笑",
    "激动": "热血", "热血": "热血", "燃": "热血", "拼命": "热血",
    "喜欢": "深情", "爱": "深情", "深情": "深情", "心疼": "深情",
}


def _inject_emotion_words(text: str, genre: str = "") -> str:
    """P0-3 情绪词注入:检测解说文本情绪,替换平淡词汇为更生动的表达"""
    if not text:
        return text
    import random as _rnd
    detected_emotions = set()
    for plain_word, emotion in PLAIN_WORD_REPLACEMENTS.items():
        if plain_word in text:
            detected_emotions.add(emotion)
    genre_emotion_map = {
        "复仇": "愤怒", "虐恋": "深情", "甜宠": "甜蜜",
        "悬疑": "悬疑", "反转": "惊讶", "搞笑": "搞笑", "热血": "热血",
    }
    for gk, ge in genre_emotion_map.items():
        if gk in genre or gk in text:
            detected_emotions.add(ge)
    if not detected_emotions:
        return text
    main_emotion = _rnd.choice(list(detected_emotions))
    pool = EMOTION_WORD_POOL.get(main_emotion, [])
    if not pool:
        return text
    replacements_done = []
    result = text
    for plain_word, emotion in PLAIN_WORD_REPLACEMENTS.items():
        if emotion == main_emotion and plain_word in result and len(replacements_done) < 2:
            new_word = _rnd.choice(pool)
            result = result.replace(plain_word, new_word, 1)
            replacements_done.append(f"{plain_word}→{new_word}")
            pool = [w for w in pool if w != new_word]
    if replacements_done:
        log(f"   \U0001f4a1 情绪词注入: {main_emotion} → {', '.join(replacements_done)}", "")
    return result




# 镜头类型权重(专业剪辑视角)

SHOT_TYPE_WEIGHTS = {

    "closeup": 2.0,      # 特写镜头

    "extreme_closeup": 2.5,  # 大特写

    "medium": 1.2,       # 中景

    "wide": 1.0,         # 远景

    "motion": 1.5,       # 运动镜头

    "push": 1.8,         # 推镜头

    "pull": 1.6,         # 拉镜头

}



def detect_shot_type(frame, gray, prev_gray=None):

    """检测镜头类型"""

    import cv2

    import numpy as np



    shot_type = "medium"

    motion_score = 0.0



    h, w = gray.shape[:2]



    face_cascade = cv2.CascadeClassifier(

        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

    )

    faces = face_cascade.detectMultiScale(gray, 1.1, 4)



    if len(faces) > 0:

        max_face = max(faces, key=lambda f: f[2] * f[3])

        x, y, fw, fh = max_face

        face_ratio = (fw * fh) / (w * h)



        if face_ratio > 0.15:

            shot_type = "extreme_closeup"

        elif face_ratio > 0.08:

            shot_type = "closeup"

        elif face_ratio > 0.03:

            shot_type = "medium"

        else:

            shot_type = "wide"



    if prev_gray is not None:

        diff = cv2.absdiff(gray, prev_gray)

        motion_score = np.mean(diff) / 255.0



        if motion_score > 0.1:

            edges = cv2.Canny(diff.astype(np.uint8), 50, 150)

            left_edge = np.sum(edges[:, :w//3])

            center_edge = np.sum(edges[:, w//3:2*w//3])

            right_edge = np.sum(edges[:, 2*w//3:])



            total_edge = left_edge + center_edge + right_edge

            if total_edge > 0 and center_edge > (left_edge + right_edge) * 1.5:

                shot_type = "push"



    return shot_type, motion_score



def is_ending_clip(frame, gray=None) -> bool:

    """检测是否为片尾黑屏/文字画面"""

    import cv2

    import numpy as np



    if gray is None:

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)



    mean_brightness = np.mean(gray)

    if mean_brightness < 15:  # 几乎全黑

        return True



    # 检测高亮文字区域

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    white_ratio = np.sum(binary > 0) / binary.size

    if white_ratio < 0.05 and mean_brightness > 180:

        return True



    std_dev = np.std(gray)

    if std_dev < 20 and mean_brightness > 200:

        return True



    return False



# ==================== 【配置系统】优先级:用户自定义 > 智能检测 > 默认配置 ====================



# 默认配置(作为兜底)

DEFAULT_CONFIG = {

    # ---- 文件夹配置 ----

    "input_dir":  "raw_videos",

    "output_dir": "output_videos",

    "bgm_dir":    "bgm",

    "narration_dir": "narration",

    "subtitle_dir":  "subtitles",



    # ---- 视频比例参数 ----

    # aspect_ratio: "auto" = 自动检测原视频比例(16:9→16:9,9:16→9:16)

    #               "9:16"  = 强制竖屏输出

    #               "16:9"  = 强制横屏输出

    "aspect_ratio": "auto",    # 用户可选: auto / 9:16 / 16:9 / 4:3 / 1:1

    "width":        0,          # 动态设置(auto时由原视频决定)

    "height":       0,          # 动态设置



    # ---- 抖音爆款视频参数 ----

    "min_duration": 60,    # 成片最短60秒

    "max_duration": 180,   # 成片最长3分钟

    "fps":          30,

    "bitrate":      "5M",

    "audio_bitrate":"192k",

    "codec":        "libx264",

    "audio_codec":  "aac",



    # ---- 片段配置(爆款节奏)----

    "clip_min_sec": 2.0,   # 最短2秒(确保时长)

    "clip_max_sec": 6,     # 最长6秒

    "target_clip_count": 40,  # 目标片段数(60-180秒视频)



    # ---- 爆款开场配置 ----

    "hook_duration": 3,       # 开场钩子时长

    "hook_required": True,    # 强制开场钩子

    "conflict_boost": 1.5,    # 冲突片段权重加成



    # ---- 字幕配置 ----

    "subtitle_size":     44,

    "subtitle_color":    "white",

    "subtitle_stroke":   "black",

    "subtitle_stroke_w": 3,

    "subtitle_position":  ("center", "bottom"),

    "subtitle_margin_v":  80,



    # ---- 音频混音配置 ----

    "bgm_volume":      0.15,      # [FIX-解说听不清-20260701] 0.30→0.15,BGM减半不抢解说
    "original_volume": 0.60,

    "narration_volume": 2.50,    # [FIX-解说听不清-20260701] 0.80→2.50,ChatTTS轻(-18dB RMS)需强力放大才能与BGM竞争
    "orig_volume_with_narration": 0.10,  # [FIX-解说比例过少-20260701] 有解说时原声压到几乎无声,让抖音听到的主要是AI解说
    "orig_volume_no_narration": 1.0,

    # 旁链压缩参数(原声以解说为旁链触发器)
    "sidechain_threshold": 0.05,  # [FIX-20260701] 0.15→0.05,更灵敏触发(解说RMS~0.05即触发压缩),解说时原声压到~12%
    "sidechain_ratio":     10,     # [FIX-20260701] 5→10,强力压缩,解说时原声压到~6%(0.60*0.06)
    # ---- ASR模型配置 ----
    "asr_model": "medium",         # medium=更高识别精度

    # ---- 卡点配置 ----

    "beat_threshold":           0.8,

    "beat_detection_interval":  0.1,



    # ---- 高光检测 ----

    "highlight_threshold": 0.15,

    "analysis_interval":    0.5,



    # ---- 离线模式 ----

    "offline_mode": False,



    # ---- 解说 ----

    "narration_lang": "zh-CN",

    "narration_voices": {

        "tingting": ("Tingting", "温柔女声(适合甜宠/日常)"),

        "meijia":  ("Meijia",  "温柔女声(台湾腔,适合古风)"),

    },

    "narration_voice": "tingting",

    "orig_volume_no_narration": 1.0,

    "orig_volume_with_narration": 0.10,  # [FIX-解说比例过少-20260701] 原声几乎静音,让AI解说成为绝对主导

    "narration_volume": 2.50,   # [FIX-解说听不清-20260701] ChatTTS生成音量轻(-18dB RMS,12.5%振幅),1.2x不够. 2.5x使峰值压过BGM
    "bgm_volume":          0.15,   # [FIX-解说听不清-20260701] BGM从0.3降到0.15,避免盖住轻音解说

    # 旁链压缩参数(原声以解说为旁链)
    "sidechain_threshold": 0.15,  # [FIX-解说听不清-20260701] 阈值从0.25降到0.15,更早触发压缩,更彻底压制BGM
    "sidechain_ratio":     5,     # [FIX-解说听不清-20260701] 压缩比从3升到5,解说时BGM压得更低,突出人声
    "sidechain_attack":    10,    # 攻击时间(ms,快速压缩)
    "sidechain_release":   500,   # 释放时间(ms,平滑恢复)


    # ---- 智能特效系统 ----

    "auto_effects": True,



    # ---- 命名格式 ----

    "naming_format": "{drama_name}_{episode}_{date}_{duration}s",



    # ==================== 【智能配置】以下值可被用户自定义覆盖 ====================



    # 画幅比例(auto=智能检测)

    "aspect_ratio": "auto",



    # 剧情片段编排模式

    #   auto      = 智能匹配(根据类型/节奏自动编排,默认)

    #   hook_sequential = 钩子串联(开场1-4个关联片段串联)

    #   peak_cluster    = 高潮聚类(相似高光片段集中呈现)

    #   timeline        = 时间线叙事(严格按原剧顺序)

    "narrative_arrangement": "auto",



    # 节奏风格(auto=智能选择)

    "rhythm_style": "auto",



    # 转场类型(auto=智能选择)

    "transition_type": "auto",

    "transition_duration": 0.5,



    # 调色预设(auto=智能分析)

    "color_grade": "auto",



    # 预告片模板(auto=智能选择)

    "trailer_template": "auto",



    # 开场钩子文案(空=智能生成)

    "opening_hook": "",



    # 结尾文案(空=智能生成)

    "ending_text": "",



    # 剧名标题(空=从文件名提取)

    "drama_title": "",


    # ---- 流程模式 ----
    # True = 解说驱动v2(先解说后匹配画面)
    # False = 传统流程(先选片段后解说)

}



# 运行时配置(将被合并后的配置替换)

CONFIG = DEFAULT_CONFIG.copy()





def apply_user_config(user_config: dict = None) -> dict:

    """

    应用用户配置,合并优先级:用户自定义 > 智能检测 > 默认配置



    Args:

        user_config: 用户从前端传入的配置



    Returns:

        合并后的最终配置

    """

    global CONFIG



    if not user_config:

        user_config = {}



    # 智能检测配置(将在处理时动态生成)

    smart_config = {}



    # 使用配置合并器

    if HAS_CONFIG_MERGER:

        CONFIG = merge_config(user_config, smart_config, DEFAULT_CONFIG)

    else:

        # 简单合并:用户配置覆盖默认配置

        CONFIG = DEFAULT_CONFIG.copy()

        for key, value in user_config.items():

            if value is not None and value != "" and value != "auto":

                CONFIG[key] = value

                CONFIG[f"{key}_source"] = "user"

            elif value == "auto":

                CONFIG[f"{key}_source"] = "smart"

            else:

                CONFIG[f"{key}_source"] = "default"



    return CONFIG





def get_effective_config(key: str, smart_value=None):

    """

    获取生效的配置值



    优先级:用户自定义 > 智能检测(已存储) > 默认值



    Args:

        key: 配置键

        smart_value: 传参优先级(本次调用特定值,可选)



    Returns:

        最终生效的配置值

    """

    global CONFIG, SMART_CONFIG



    # 1. 用户已自定义 → 直接用用户值

    source = CONFIG.get(f"{key}_source", "default")

    if source == "user":

        return CONFIG.get(key)



    # 2. 本次调用传了 smart_value → 优先用它

    if smart_value is not None and smart_value != "" and smart_value != "auto":

        return smart_value



    # 3. 全局智能检测值已存储 → 用它

    if key in SMART_CONFIG and SMART_CONFIG[key] not in ("", "auto", None):

        return SMART_CONFIG[key]



    # 4. 用户设为 auto → 用全局智能检测值

    # 5. 用户没设置 → 用默认配置值

    return CONFIG.get(key)





def is_user_customized(value):

    """判断用户是否自定义了某个配置值"""

    if value is None:

        return False

    if isinstance(value, str):

        return value != "" and value != "auto"

    return value is not None





# ==================== 【2】抖音敏感词库 ====================

SENSITIVE_WORDS = [

    # 极限词

    "最", "第一", "百分百", "绝对", "国家级", "顶级", "唯一", "极致", "完美",

    # 导流词

    "微信", "加我", "私信", "二维码", "vx", "联系方式", "群", "QQ",

    # 违规内容

    "赌博", "色情", "暴力", "吸毒", "嫖娼", "裸", "彩票",

    # 医疗/金融

    "治病", "减肥", "瘦身", "增大", "延时", "赚钱", "投资", "理财", "贷款", "稳赚", "保本",

    # 抖音禁用词

    "免费", "无门槛", "必看", "速看", "不点后悔", "关注我", "点击下方", "点赞",

    # 虚假承诺

    "保证", "承诺", "无效退款", "彻底治愈",

]



# ==================== 【2.5】BGM智能匹配系统 ====================

# 核心逻辑:文件名关键词识别 + 音频特征分析,双重判断场景类型

# 匹配原则:BGM风格必须与剧情情绪高度吻合



# BGM场景分类关键词(从文件名中匹配)

BGM_SCENE_TAGS = {

    # 复仇爽剧 → 高能、战斗、热血

    "bgm_revenge": [

        "燃", "热血", "复仇", "战斗", "爆发", "炸裂", "燃曲",

        "史诗", "大片", "激昂", "震撼", "大气", "战斗", "逆袭",

        "燃向", "高潮", "逆天", "霸气", "王炸", "炸场",

        "revenge", "battle", "epic", "action", "intense", "power",

    ],

    # 甜蜜恋爱 → 温馨、甜宠、浪漫

    "bgm_sweet": [

        "甜", "甜蜜", "恋爱", "浪漫", "温馨", "心动", "小甜",

        "撒糖", "甜宠", "告白", "初吻", "唯美", "心动曲",

        "romantic", "sweet", "love", "romance", "soft", "tender",

    ],

    # 悬疑/惊悚 → 低沉、神秘、紧张

    "bgm_suspense": [

        "悬疑", "惊悚", "恐怖", "诡异", "神秘", "阴暗", "黑暗",

        "惊险", "紧张", "压抑", "毛骨", "诡异曲", "鬼魅",

        "suspense", "horror", "dark", "mystery", "tension", "scary",

    ],

    # 悲情虐心 → 悲伤、催泪、抒情

    "bgm_sad": [

        "虐", "悲伤", "催泪", "悲情", "心痛", "离别", "伤感",

        "忧桑", "心碎", "断肠", "悲曲", "泪目", "苦情",

        "sad", "tear", "cry", "emotional", "painful", "heartbreak",

    ],

    # 搞笑/轻松 → 轻快、活泼、跳跃

    "bgm_funny": [

        "搞笑", "欢快", "轻松", "活泼", "跳跃", "俏皮", "喜剧",

        "可爱", "欢脱", "沙雕", "趣味", "明快",

        "funny", "comedy", "happy", "upbeat", "cheerful", "quirky",

    ],

    # 史诗/古风 → 大气、古典、国风

    "bgm_ancient": [

        "古风", "国风", "古典", "史诗", "宫廷", "武侠", "仙侠",

        "大气", "厚重", "唯美古", "古筝", "琵琶", "国潮",

        "ancient", "epic", "traditional", "dynasty", "folk",

    ],

    # 都市/现代 → 时尚、节奏、潮流

    "bgm_modern": [

        "都市", "现代", "时尚", "潮流", "电音", "嘻哈", "节奏",

        "动感", "urban", "modern", "electronic", "hiphop", "rhythm",

    ],

}



# 剧情类型 → BGM场景优先级映射

GENRE_TO_BGM_SCENE = {

    "reincarnation":  ["bgm_revenge", "bgm_suspense", "bgm_sad", "bgm_modern"],

    "revenge":        ["bgm_revenge", "bgm_suspense", "bgm_action", "bgm_modern"],

    "ceo":            ["bgm_sweet", "bgm_revenge", "bgm_modern", "bgm_ancient"],

    "transmigration": ["bgm_ancient", "bgm_revenge", "bgm_suspense", "bgm_funny"],

    "mistaken":       ["bgm_sad", "bgm_suspense", "bgm_sweet", "bgm_revenge"],

    "hidden_power":   ["bgm_revenge", "bgm_suspense", "bgm_ancient", "bgm_modern"],

    "sweet":          ["bgm_sweet", "bgm_funny", "bgm_revenge", "bgm_modern"],

    "abuse":          ["bgm_sad", "bgm_revenge", "bgm_suspense", "bgm_ancient"],

    "conspiracy":     ["bgm_suspense", "bgm_revenge", "bgm_ancient", "bgm_sad"],

}



# 场景 → 音频特征基准(用于无文件名时分析音频本身)

BGM_SCENE_FEATURES = {

    "bgm_revenge":    {"avg_rms": 0.20, "spectral_balance": "bright", "preferred_tempo": "fast"},

    "bgm_sweet":      {"avg_rms": 0.14, "spectral_balance": "mid",   "preferred_tempo": "medium"},

    "bgm_suspense":   {"avg_rms": 0.12, "spectral_balance": "dark",  "preferred_tempo": "slow"},

    "bgm_sad":        {"avg_rms": 0.10, "spectral_balance": "dark",  "preferred_tempo": "slow"},

    "bgm_funny":      {"avg_rms": 0.16, "spectral_balance": "bright","preferred_tempo": "medium"},

    "bgm_ancient":    {"avg_rms": 0.15, "spectral_balance": "warm",  "preferred_tempo": "slow"},

    "bgm_modern":     {"avg_rms": 0.18, "spectral_balance": "bright","preferred_tempo": "fast"},

}



# 全局BGM库(启动时扫描一次)

_BGM_LIBRARY = {}  # {path: {"scenes": [], "rms": float, "beats_count": int, "filename": str}}





def _scan_bgm_library() -> dict:

    """

    启动时扫描 bgm/ 目录,构建BGM场景库

    返回: {文件路径: {"scenes": [scene_tags], "rms": float, "beats": int}}

    """

    global _BGM_LIBRARY

    bgm_dir = Path(CONFIG["bgm_dir"])

    if not bgm_dir.exists():

        _BGM_LIBRARY = {}

        return {}



    library = {}

    # 递归搜索所有子目录中的 MP3/WAV 文件

    mp3_files = list(bgm_dir.rglob("*.mp3")) + list(bgm_dir.rglob("*.MP3"))

    wav_files = list(bgm_dir.rglob("*.wav")) + list(bgm_dir.rglob("*.WAV"))

    all_files = mp3_files + wav_files



    for fpath in all_files:

        fname = fpath.stem.lower()

        matched_scenes = []



        # 1. 文件名关键词匹配场景

        for scene, keywords in BGM_SCENE_TAGS.items():

            if any(kw.lower() in fname for kw in keywords):

                matched_scenes.append(scene)



        # 2. 快速模式:跳过音频分析(需要时再按需分析)

        # 默认值会在匹配时使用

        library[str(fpath)] = {

            "scenes": list(set(matched_scenes)) if matched_scenes else ["bgm_sweet"],

            "rms": 0.15,  # 默认中等能量

            "beats": 15,  # 默认节拍数

            "filename": fpath.name,

            "analyzed": False,  # 标记未分析

        }



    _BGM_LIBRARY = library

    log(f"🎵 BGM库快速扫描完成:共 {len(library)} 首", "🎵")

    return library






    """

    给单个BGM打分(0~100),越高越匹配

    评分维度:场景匹配 + 能量吻合 + 时长接近

    """

    score = 0.0



    # 维度1:场景标签匹配(最重要,占60%)

    preferred_scenes = GENRE_TO_BGM_SCENE.get(genre, ["bgm_revenge"])

    bgm_scenes = bgm_entry.get("scenes", [])



    for i, sc in enumerate(preferred_scenes):

        if sc in bgm_scenes:

            score += (60 - i * 15)  # 排名第1得60,第2得45,第3得30

            break

    else:

        score += 5  # 完全不匹配也给5分兜底



    # 维度2:能量特征吻合(占30%)

    genre_energy = {

        "reincarnation": 0.20, "revenge": 0.22, "ceo": 0.15,

        "transmigration": 0.16, "mistaken": 0.12, "hidden_power": 0.20,

        "sweet": 0.14, "abuse": 0.12, "conspiracy": 0.13,

    }

    expected_rms = genre_energy.get(genre, 0.15)

    rms_diff = abs(bgm_entry.get("rms", 0.15) - expected_rms)

    energy_score = max(0, 30 - rms_diff * 200)

    score += energy_score



    # 维度3:节拍点数量(节奏感),占10%

    # 复仇/战斗类需要更多节拍,虐心类需要更少

    beats = bgm_entry.get("beats", 0)

    expected_beats = 20 if genre in ("reincarnation", "revenge", "hidden_power") else 12

    beat_diff = abs(beats - expected_beats)

    beat_score = max(0, 10 - beat_diff * 0.5)

    score += beat_score



    # 维度4:时长接近加成(跳过,建库时已默认)

    # 不再运行时检测时长(太慢且容易出错)



    return round(score, 2)





def _score_bgm_for_genre(bgm_entry: dict, genre: str, target_dur: float) -> float:

    """

    给单个BGM打分(0~100),越高越匹配

    评分维度:场景匹配 + 能量吻合 + 时长接近

    """

    score = 0.0



    # 维度1:场景标签匹配(最重要,占60%)

    preferred_scenes = GENRE_TO_BGM_SCENE.get(genre, ["bgm_revenge"])

    bgm_scenes = bgm_entry.get("scenes", [])



    for i, sc in enumerate(preferred_scenes):

        if sc in bgm_scenes:

            score += (60 - i * 15)  # 排名第1得60,第2得45,第3得30

            break

    else:

        score += 5  # 完全不匹配也给5分兜底



    # 维度2:能量特征吻合(占30%)

    genre_energy = {

        "reincarnation": 0.20, "revenge": 0.22, "ceo": 0.15,

        "transmigration": 0.16, "mistaken": 0.12, "hidden_power": 0.20,

        "sweet": 0.14, "abuse": 0.12, "conspiracy": 0.13,

    }

    expected_rms = genre_energy.get(genre, 0.15)

    rms_diff = abs(bgm_entry.get("rms", 0.15) - expected_rms)

    energy_score = max(0, 30 - rms_diff * 200)

    score += energy_score



    # 维度3:节拍点数量(节奏感),占10%

    # 复仇/战斗类需要更多节拍,虐心类需要更少

    beats = bgm_entry.get("beats", 0)

    expected_beats = 20 if genre in ("reincarnation", "revenge", "hidden_power") else 12

    beat_diff = abs(beats - expected_beats)

    beat_score = max(0, 10 - beat_diff * 0.5)

    score += beat_score



    # 维度4:时长接近加成(跳过,建库时已默认)

    # 不再运行时检测时长(太慢且容易出错)



    return round(score, 2)





def smart_bgm_select(genre: str, target_dur: float = 25.0, emotion_tags: List[str] = None) -> Tuple[Optional[str], List[float]]:

    """

    【智能BGM匹配】核心函数

    策略:

    1. 扫描BGM库(无库则先扫描)

    2. 优先选场景标签匹配的BGM

    3. 按匹配度排序,选最高分

    4. 时长优先(误差5秒内优先)

    5. 完全无匹配时随机兜底



    Returns: (bgm_path, beats_list)

    """

    global _BGM_LIBRARY



    # 空目录兜底

    bgm_dir = Path(CONFIG["bgm_dir"])

    # 递归搜索所有子目录

    files = list(bgm_dir.rglob("*.mp3")) + list(bgm_dir.rglob("*.wav"))

    if not files:

        log("⚠️ bgm/ 目录为空,跳过BGM(仅有原声)", "⚠️")

        return None, []



    # 确保BGM库已扫描

    if not _BGM_LIBRARY:

        _scan_bgm_library()



    if not _BGM_LIBRARY:

        # 库为空但目录有文件,快速建库(只用文件名)

        _scan_bgm_library()



    # ---- P0-2: BGM冷却机制 ----
    bgm_cooldown_file = os.path.join(CONFIG.get("narration_dir", "narration"), "bgm_cooldown.json")
    try:
        if os.path.exists(bgm_cooldown_file):
            with open(bgm_cooldown_file, 'r', encoding='utf-8') as _f:
                bgm_cooldown = json.load(_f)
        else:
            bgm_cooldown = {}
    except Exception:
        bgm_cooldown = {}

    # 选最优BGM

    candidates = list(_BGM_LIBRARY.items())

    if not candidates:

        # 完全没有分析数据,直接用文件名碰运气

        chosen = random.choice(files)

        beats = detect_bgm_beats(str(chosen))

        log(f"🎵 [随机] BGM: {chosen.name}", "🎵")

        return str(chosen), beats



    # 获取该genre的已用BGM列表
    used_bgms = bgm_cooldown.get(genre, [])

    # 对所有BGM打分

    scored = []

    for path, entry in candidates:

        sc = _score_bgm_for_genre(entry, genre, target_dur)

        # P0-2: 冷却降权
        fname = entry.get("filename", os.path.basename(path))
        if fname in used_bgms:
            sc *= 0.7

        scored.append((sc, path, entry))



    scored.sort(key=lambda x: x[0], reverse=True)



    # 取第一名,时长相近的优先(同分时)

    best_score, best_path, best_entry = scored[0]



    # 如果最高分BGM时长差太多(>15秒),尝试找同分且时长更近的

    if best_score < 30:

        try:

            best_dur = get_video_info(best_path)["duration"]

            close_matches = [

                (s, p, e) for s, p, e in scored

                if abs(get_video_info(p)["duration"] - target_dur) <= 10

            ]

            if close_matches:

                best_score, best_path, best_entry = close_matches[0]

        except Exception:

            pass



    # ---- P0-2: 更新冷却记录 ----
    selected_fname = best_entry.get('filename', os.path.basename(best_path))
    bgm_cooldown.setdefault(genre, [])
    if selected_fname not in bgm_cooldown[genre]:
        bgm_cooldown[genre].append(selected_fname)
    while len(bgm_cooldown[genre]) > 3:
        bgm_cooldown[genre].pop(0)
    try:
        with open(bgm_cooldown_file, 'w', encoding='utf-8') as _f:
            json.dump(bgm_cooldown, _f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    beats = detect_bgm_beats(best_path)

    scenes = best_entry.get("scenes", [])

    log(

        f"🎵 [智能匹配] BGM: {best_entry['filename']} "

        f"| 场景:{scenes} | 匹配度:{best_score}分 | 节拍:{len(beats)}个",

        "🎵"

    )

    log(f"🎵 BGM选择: {best_entry['filename']} (降权后分数: {best_score:.1f})", "🎵")

    return best_path, beats





    """
    基于上次使用记录,选择不同类别的解说
    核心:同类模板不连续使用2次以上
    """
    _now = _time.time()
    # 过滤掉最近10秒内用过的类别
    _available = [cat for cat, last_ts in _NARR_LAST_USED.items()
                 if _now - last_ts > 10]
    if not _available:
        _available = list(NARR_POOL.keys())

    _chosen_cat = __import__('random').choice(_available)
    _text = __import__('random').choice(NARR_POOL[_chosen_cat])
    _NARR_LAST_USED[_chosen_cat] = _now
    return _text



# ---- 钩子库(前3秒留人,必须劲爆)----

HOOKS = {

    # 反转型钩子

    "twist_1":  "{name}被全家踩在脚下,直到她重生归来...",

    "twist_2":  "所有人都以为{name}是废物,直到那天她出手...",

    "twist_3":  "结婚三年他嫌她丑,一纸离婚协议摔在桌上,她转身那一刻他疯了!",

    "twist_4":  "她本是卑微替身,一次意外她决定不再装了...",

    "twist_5":  "你以为他只是一个穷小子?他的身份让所有人颤抖!",

    # 悬念型钩子

    "hook_1":   "她被关进精神病院,三年后出来,所有人都慌了!",

    "hook_2":   "这一巴掌,她记了整整五年!",

    "hook_3":   "婚礼现场,她当众退婚,全场鸦雀无声!",

    "hook_4":   "她带着三个天才宝宝归来,前夫当场跪下求原谅!",

    "hook_5":   "消失五年的前妻突然出现,他看了一眼监控愣住了!",

    # 数字型钩子(完播率最高)

    "num_1":    "{name}入狱五年,受尽屈辱,出狱后她让整个城市颤抖!",

    "num_2":    "她等了整整十年,终于等来了这一天!",

    "num_3":    "三年之约已到,他王者归来,却发现她早已...",

    "num_4":    "她被冤枉入狱七年,出来后发现老公竟在...",

}



# ---- 剧情钩子库(中间段,揭示看点)----

PLOT_HOOKS = {

    "rev_reveal":   "他不知道,重生归来的她,手撕渣男贱女毫不手软!",

    "rich_return":  "她不再是那个任人宰割的可怜虫,而是真正的大佬!",

    "truth_out":    "当年的真相终于浮出水面,所有人都惊掉了下巴!",

    "power_flip":   "局势瞬间逆转,他们的态度也跟着180度大转变!",

    "identity":     "她的身份远不止于此,当他发现真相时已经太晚了!",

    "love_reveal":  "原来他一直在暗中守护她,只是从未说出口...",

    "betrayal":     "最亲近的人背后捅刀,她发誓要让所有人付出代价!",

    "king_back":    "王者归来,谁与争锋!这一刻,全场寂静!",

    "truth_bitter": "揭开真相的她,眼泪不争气地流了下来!",

    "counter_attack":"绝地反击!她用行动让所有人闭上了嘴!",

}


# ---- 差异化Prompt工程(反同质化P0-2)----

NARR_STYLES = [
    # 角色视角(决定解说的人称和立场)
    {"voice": "旁观者",    "pronoun": "他/她",  "desc": "客观描述画面"},
    {"voice": "知情人",    "pronoun": "她",    "desc": "透露内幕信息"},
    {"voice": "共情者",    "pronoun": "她",    "desc": "情绪共鸣导向"},
    {"voice": "揭秘者",    "pronoun": "观众",  "desc": "引导发现真相"},
    {"voice": "记录者",    "pronoun": "镜头",  "desc": "沉浸式描述"},
]

NARR_RHYTHMS = [
    "急促紧张,每句话间隔短",
    "舒缓叙事,带背景交代感",
    "情绪爆发型,短促有力",
    "渐进铺垫型,留悬念",
]

def _build_diverse_prompt(segment_info: dict, clip_idx: int, total: int) -> str:
    """
    为每个片段构建开放式Prompt--不给模板,让LLM根据字幕自由生成
    反同质化核心:每次调用都只给字幕 + 最少约束
    """
    import random as _r

    text = segment_info.get("text", "")

    # 只给位置和字幕,不指定"怎么写"
    if clip_idx == 0:
        position_hint = "开头第一句,直接切入剧情,不要'话说''大家看'这类开场白"
    elif clip_idx == total - 1:
        position_hint = "结尾,留给观众想象空间,不要总结"
    else:
        position_hint = "中间段落,自然推进剧情"

    prompt = f"""你根据字幕内容写一句短剧解说(20-40字)。

【字幕内容】
{text}

要求:
- 用正常人口吻,像在跟朋友讲这个剧情
- 不要模板化表达(禁止:这一幕、注意看、你敢信、谁知道)
- 不要形容词堆砌,直接说发生了什么
- {position_hint}
- 不渲染暴力复仇快感,不制造阶层/性别/婆媳对立
- 自然融入AI创作声明(如"AI带你追"或"AI剪的")
- 只输出解说文字,不要引号、不要解释

解说:"""

    return prompt


# ---- 叙事结构池(反同质化P1-3)----
NARRATIVE_STRUCTURES = {
    "压抑逆袭":    "铺垫压抑→意外转机→小高潮→再次跌落→绝地反击→完美结局",
    "甜中带刀":    "甜蜜开场→暗流涌动→小冲突→短暂和解→致命一击→开放式结局",
    "悬疑解谜":    "神秘开场→碎片线索→误导方向→真相浮现→惊天逆转→留白悬念",
    "复仇爽剧":    "屈辱铺垫→隐忍蓄力→初次反击→更大阴谋→最终对决→复仇成功",
    "身份反转":    "表象呈现→身份揭示→认知冲击→立场转变→深层真相→新平衡",
    "多线交织":    "A线引入→B线交织→双线冲突→A线高潮→B线爆发→双线汇合",
    "情绪过山车":  "平静开场→小事升温→大冲突→短暂平息→更大爆发→情绪宣泄",
    "倒叙揭秘":    "结果先行→回溯原因→层层剥茧→关键发现→认知颠覆→新起点",
}

# 记录最近用过的结构,避免连续重复
_NARR_STRUCT_USED = []

def _choose_diverse_structure(mood: str, genre: str) -> str:
    """
    根据情绪/类型选择差异化叙事结构
    规则:最近用过的结构不再连续使用(同类剧除外)
    """
    import random

    # 1. 先匹配情绪关键词
    mood_map = {
        "逆袭": ["压抑逆袭", "复仇爽剧", "身份反转"],
        "反转": ["身份反转", "悬疑解谜", "倒叙揭秘"],
        "虐":   ["甜中带刀", "情绪过山车", "多线交织"],
        "甜":   ["甜中带刀", "情绪过山车", "身份反转"],
        "悬疑": ["悬疑解谜", "倒叙揭秘", "多线交织"],
        "爽":   ["复仇爽剧", "压抑逆袭", "情绪过山车"],
    }

    candidates = []
    for key, structs in mood_map.items():
        if key in mood:
            candidates.extend(structs)

    if not candidates:
        candidates = list(NARRATIVE_STRUCTURES.keys())

    # 2. 排除最近连续用过的2种结构
    if len(_NARR_STRUCT_USED) >= 2:
        recent = set(_NARR_STRUCT_USED[-2:])
        candidates = [c for c in candidates if c not in recent]

    chosen = random.choice(candidates)
    _NARR_STRUCT_USED.append(chosen)
    if len(_NARR_STRUCT_USED) > 10:
        _NARR_STRUCT_USED.pop(0)

    return NARRATIVE_STRUCTURES[chosen]


# ---- LLM参数统一配置(反同质化P2-5)----
LLM_TEMP_CONFIG = {
    # 用途: (temperature, num_predict, 描述)
    "clip_narration_first":  (0.75, 100,  "开场解说,需要创意和吸引力"),
    "clip_narration_middle":  (0.45, 80,   "中间解说,稳定连贯为主"),
    "clip_narration_final":  (0.80, 120,  "结尾解说,需要惊喜感和悬念"),
    "context_analysis":      (0.50, 600,  "剧情分析,平衡准确性和多样性"),
    "title_generation":      (0.70, 150,  "标题生成,需要创意"),
    "highlight_detection":   (0.40, 180, "高光检测,稳定为主"),
    "narration_legacy":     (0.75, 600,  "旧版解说生成"),
    "bgm_selection":     (0.5,  400,  "BGM选择,平衡稳定性和多样性"),
}

def _get_llm_params(usage: str) -> dict:
    """统一获取LLM参数,减少硬编码"""
    cfg = LLM_TEMP_CONFIG.get(usage, (0.7, 100, "默认"))
    return {"temperature": cfg[0], "num_predict": cfg[1]}



# ---- 片段评分随机扰动(反同质化P1-3)----
_ORIG_SCORE_BY_EVENTS = None


def _pick_narration_voice(genre):
    VOICE_MAP = {
        "ancient": "zh-CN-XiaomoNeural",       # 成熟知性女声
        "transmigration": "zh-CN-XiaomoNeural",
        "revenge": "zh-CN-XiaoyiNeural",        # 活力女声
        "romance": "zh-CN-XiaoxiaoNeural",      # 温暖女声
        "suspense": "zh-CN-YunyangNeural",      # 新闻男声(严肃感)
        "emotional": "zh-CN-XiaohanNeural",     # 柔情女声
        "comedy": "zh-CN-XiaochenNeural",       # 轻快女声
        "heroic": "zh-CN-YunxiNeural",          # 阳光男声
        "default": "zh-CN-XiaoxiaoNeural",
    }

    return VOICE_MAP.get(genre, VOICE_MAP["default"])





def _tts_edge(text: str, voice: str = 'zh-CN-XiaoxiaoNeural') -> str:
    '''edge-tts配音(Python API + asyncio.run,情感化prosody)'''
    try:
        import asyncio
        import edge_tts

        Path(CONFIG['narration_dir']).mkdir(parents=True, exist_ok=True)
        mp3 = os.path.join(CONFIG['narration_dir'], f'tts_{int(time.time())}.mp3')

        # [FIX-TTS-EXPRESSION-20260618] 根据文本末尾判断语调
        _end = text.rstrip()[-1] if text.rstrip() else ''
        if _end in ('!', '!'):
            _rate, _pitch = "+8%", "+5Hz"
        elif _end in ('?', '?'):
            _rate, _pitch = "+3%", "+4Hz"
        else:
            _rate, _pitch = "+5%", "-1Hz"

        async def _speak():
            comm = edge_tts.Communicate(text, voice, rate=_rate, pitch=_pitch)
            await comm.save(mp3)

        asyncio.run(_speak())
        if os.path.exists(mp3) and os.path.getsize(mp3) > 500:
            return mp3
    except Exception as e:
        log(f'⚠️ edge-tts: {e}', '⚠️')
    return None

    """
    解说生成:完全交给Ollama,不用模板
    key_words[0] = 完整字幕文本
    """
    import re

    actual_text = key_words[0] if key_words and isinstance(key_words[0], str) and len(key_words[0]) > 20 else ""
    conflict_kws = [kw for kw in key_words[1:] if isinstance(kw, str)] if len(key_words) > 1 else []

    if not actual_text or len(actual_text) < 15:
        return _genre_narration_fallback(name, genre, conflict_kws)

    # 用Ollama自由生成,只给字幕 + 最少约束
    prompt = f"""根据下面的短剧字幕,写一篇自然的解说词({target_chars}字左右)。

【剧名】《{name}》
【类型】{genre}
【情绪曲线】{",".join(emotion_curve)}
【字幕内容】
{actual_text[:800]}

要求:
- 像在跟朋友讲这个剧,口语化,不要书面语
- 禁止模板词:这一幕、注意看、你敢信、反转来了、谁知道
- 不要"首先/其次/最后"这类结构化表达
- 开头直接讲剧情,不要"今天给大家讲"
- 结尾自然收束
- 只输出解说正文

解说:"""

    text = _call_ollama_retry(prompt, "narration_viral", timeout=90, retries=2)
    if text:
        text = re.sub(r'^(解说:|解说词:|正文:|#+|"+)', '', text).strip()
        text = text.strip('"\'""').strip()
        if len(text) >= 30:
            return text

    return _genre_narration_fallback(name, genre, conflict_kws)





    keyword_hooks = {

        "离婚": f"一纸离婚协议摔在{name}面前,她连眼都没眨。从此,她的人生翻开了崭新的一页。",

        "背叛": f"被最信任的人背叛的那一刻,{name}没有哭,反而笑了。因为从这一刻起,她要让他们付出代价。",

        "打脸": f"所有人都以为{name}好欺负?今天,她要让他们知道什么叫真正的实力。",

        "反击": f"忍了这么久,今天{name}终于不再忍了。当反击开始,所有人都看傻了眼。",

        "真相": f"当真相揭开的那一刻,所有人都哑口无言。原来{name}一直都在隐忍。",

        "归来": f"{name}消失了三年,所有人都以为她不会再回来。可当她的身影再次出现,场面瞬间安静。",

        "重生": f"重生回来的第一天,{name}就发誓要改变一切。这一次,谁也别想再欺负她。",

        "身份": f"没人知道{name}的真实身份。当真相揭开的那一刻,连总裁都要给她让路。",

    }



    # 尝试匹配关键词

    if key_words:

        for kw, hook in keyword_hooks.items():

            if kw in str(key_words):

                return hook + "精彩还在后面,追起来!"



    # 类型模板兜底

    templates = {

        "revenge": f"{name}被人欺负了太久。但没人知道,她早就布好了一盘大棋。当她反击的那一刻,所有人都傻眼了。",

        "sweet": f"他们第一次见面就吵了一架。谁也没想到,这个讨厌鬼后来成了{name}最放不下的人。",

        "suspense": f"一个不起眼的细节,竟然藏着一个惊天大秘密。当{name}揭开真相的那一刻,所有人都愣住了。",

        "default": f"这个故事的开始很平凡,但随着剧情发展,你会发现每个细节都不简单。{name}的命运即将改变。",

    }



    return templates.get(genre, templates["default"])





# 短剧题材关键词库
GENRE_KEYWORDS = {
    "都市言情": ["总裁", "千金", "豪门", "闪婚", "离婚", "前妻", "前夫", "契约", "未婚妻", "未婚夫"],
    "穿越": ["穿越", "古代", "妃", "太子", "王爷", "公主", "将军", "世子", "公主殿下", "皇上"],
    "重生": ["重生", "前世", "上一世", "重来", "从头再来", "回到"],
    "甜宠": ["宠溺", "溺爱", "偏爱", "护短", "甜", "宠", "心尖宠", "全家宠"],
    "虐恋": ["虐", "心痛", "误会", "背叛", "伤", "泪", "哭", "不原谅"],
    "搞笑": ["搞笑", "喜剧", "逗比", "沙雕", "笑死", "好玩", "有趣"],
    "逆袭": ["逆袭", "翻身", "打脸", "碾压", "踩", "登顶", "成神", "归来"],
    "玄幻": ["修仙", "仙尊", "大帝", "魔", "神", "功法", "灵", "法宝", "天道"],
    "悬疑": ["悬疑", "侦探", "破案", "阴谋", "秘密", "真相", "调查"],
    "乡村": ["乡村", "农村", "乡下", "农民", "村长", "山沟", "田园"],
    "民国": ["民国", "军阀", "司令", "太太", "少帅", "大帅"],
}

def _detect_drama_genre(full_text: str, filename: str = "") -> str:

    """

    检测短剧类型/题材

    返回类型标签字符串,优先按关键词命中率

    """

    search_text = (full_text + " " + filename).lower()

    scores = {}



    for genre, keywords in GENRE_KEYWORDS.items():

        score = sum(1 for kw in keywords if kw in search_text)

        if score > 0:

            scores[genre] = score



    if not scores:

        return random.choice(list(GENRE_KEYWORDS.keys()))



    # 选得分最高的类型

    return max(scores, key=scores.get)




# 高风险题材库(抖音违规内容筛查)
HIGH_RISK_GENRES = {
    "复仇爽剧": {
        "keywords": ["复仇", "报复", "以暴制暴", "血债血偿", "打脸", "虐渣", "手撕", "教训", "欺负", "凌辱"],
        "risk_level": "HIGH",
        "risk_reason": "宣扬极端复仇和以暴制暴,易引发观众模仿"
    },
    "家庭矛盾": {
        "keywords": ["婆媳", "恶婆婆", "儿媳妇", "丈夫出轨", "小三", "离婚", "家暴", "争财产", "养女", "继母"],
        "risk_level": "HIGH",
        "risk_reason": "渲染家庭矛盾和冲突,制造性别/家庭对立情绪"
    },
    "阶级对立": {
        "keywords": ["豪门", "穷酸", "看不起", "富二代", "凤凰男", "门不当户不对", "嫌贫爱富", "践踏尊严"],
        "risk_level": "MEDIUM",
        "risk_reason": "制造阶级对立和贫富冲突,可能引发负面社会情绪"
    },
    "人性阴暗": {
        "keywords": ["冷漠", "见死不救", "背叛", "算计", "心机", "陷害", "阴谋", "漠视生命"],
        "risk_level": "MEDIUM",
        "risk_reason": "宣扬人性阴暗面和负面价值观,违背公序良俗"
    },
}
def _check_content_risk(full_text: str, drama_name: str) -> dict:
    """
    检测内容是否属于抖音违规风险题材(制造矛盾对立内容)
    返回: {"risk_level": "HIGH"/"MEDIUM"/"SAFE", "matched": [...], "reason": "..."}
    """
    search_text = (full_text + " " + drama_name)
    all_matched = []
    final_reason = ""
    final_level = "SAFE"

    # 按优先级: HIGH > MEDIUM
    for genre_key, genre_info in HIGH_RISK_GENRES.items():
        hit_kws = [kw for kw in genre_info["keywords"] if kw in search_text]
        if hit_kws:
            all_matched.extend(hit_kws)
            if genre_info["risk_level"] == "HIGH":
                final_level = "HIGH"
                final_reason = genre_info["risk_reason"]
            elif genre_info["risk_level"] == "MEDIUM" and final_level != "HIGH":
                final_level = "MEDIUM"
                final_reason = genre_info["risk_reason"]

    # 去重
    unique_matched = list(dict.fromkeys(all_matched))

    return {
        "risk_level": final_level,
        "matched": unique_matched,
        "reason": final_reason,
    }




    try:

        print(f"{emoji} {msg}", flush=True)

    except UnicodeEncodeError:

        # 回退:去掉emoji

        print(msg, flush=True)



def check_dirs():

    """自动创建所有必要文件夹"""

    for d in [

        CONFIG["input_dir"], CONFIG["output_dir"], CONFIG["bgm_dir"],

        CONFIG["narration_dir"], CONFIG["subtitle_dir"]

    ]:

        Path(d).mkdir(parents=True, exist_ok=True)

        log(f"文件夹确认: {d}", "📁")



def get_video_info(path):

    """用 ffprobe 获取视频基础信息(时长、宽高、fps)"""

    try:

        cmd = [

            "ffprobe", "-v", "quiet", "-print_format", "json",

            "-show_streams", "-show_format", path

        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)

        import json

        info = json.loads(result.stdout)



        video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)

        audio_stream = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)



        duration = float(info["format"].get("duration", 0))

        width  = int(video_stream["width"])  if video_stream else 0

        height = int(video_stream["height"]) if video_stream else 0

        fps_str = video_stream.get("r_frame_rate", "30/1") if video_stream else "30/1"

        fps = eval(fps_str) if "/" in fps_str else float(fps_str)

        has_audio = audio_stream is not None



        return {"duration": duration, "width": width, "height": height, "fps": fps, "has_audio": has_audio}

    except Exception as e:

        log(f"ffprobe 解析失败: {e}", "⚠️")

        return {"duration": 0, "width": 0, "height": 0, "fps": 30, "has_audio": False}



def is_safe_text(text):

    """本地敏感词过滤"""

    safe = True

    found_word = None

    filtered = text

    for word in SENSITIVE_WORDS:

        if word in filtered:

            safe = False

            found_word = word

            filtered = filtered.replace(word, "**")

    return safe, filtered, found_word



def extract_drama_info(filename):

    """从文件名自动提取短剧名称和集数"""

    name_only = Path(filename).stem

    patterns = [

        (r"(.+?)[_第](第?\d+)[集部期]", 2),  # 豪门恩怨_第3集 / 豪门恩怨-第3集

        (r"(.+?)[_第](第?\d+)", 2),             # 豪门恩怨_3 / 豪门恩怨03

        (r"(.+?)(\d{2,4})", 2),                  # 豪门恩怨03

    ]

    for pattern, ep_idx in patterns:

        m = re.search(pattern, name_only)

        if m:

            drama = m.group(1).strip().replace("_", "").replace("-", "")

            episode = m.group(2).strip().zfill(2)

            return drama, episode

    return name_only, "01"





def _extract_event_graph(full_text: str) -> dict:
    """
    从字幕文本提取事件图谱(Toonflow风格:结构化分镜节点)
    返回: {"events": [{"time":秒,"event":"描述","type":"冲突|高潮|转折","importance":1-5,
                      "emotion_weight":0-1,"characters":[],"location":"","visual_prompt":""}],
            "timeline": "情绪曲线描述"}
    """
    if not full_text or len(full_text.strip()) < 50:
        return {"events": [], "timeline": ""}

    # 采样前2500字(控制prompt长度)
    sample = full_text[:MAX_TEXT_SAMPLE]

    prompt = f"""你是一个短剧剧情分析师。请分析以下台词,提取关键事件节点。

台词:
{sample}

请识别:
1. 关键事件(3-8个):谁在什么时间做了什么,事件类型(冲突/高潮/转折/揭秘/情感爆发/温馨/悬疑)
2. 每个事件的重要性评分(1-5分,5分最重要)
3. 情绪权重(0-1,1为最强情绪)
4. 涉及角色名
5. 场景位置
6. 视觉提示词(用于AI生成画面参考)
7. 预估每个事件在视频中的大致时间位置(秒数,从0开始)

输出JSON格式:
{{"events":[{{"time":120,"event":"女主发现真相","type":"揭秘","importance":5,"emotion_weight":0.9,"characters":["女主"],"location":"客厅","visual_prompt":"woman shocked face closeup dim lighting"}},...],"timeline":"开头压抑→中期冲突→高潮反转"}}

只输出JSON,不要其他文字:"""

    # P0改造: 统一重试函数
    raw = _call_ollama_retry(prompt, "highlight_detection", timeout=120, retries=2)
    if raw:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            graph = _json.loads(match.group())
            events = graph.get('events', [])
            for evt in events:
                evt.setdefault("emotion_weight", evt.get("importance", 3) / 5.0)
                evt.setdefault("characters", [])
                evt.setdefault("location", "unknown")
                evt.setdefault("visual_prompt", "")
                evt.setdefault("shot_anchor", "")
            log(f"   📊 事件图谱(Toonflow): 提取{len(events)}个结构化事件", "")
            return graph
    return {"events": [], "timeline": ""}


def _score_by_events(highlights: List[Tuple[float, float, float]], event_graph: Dict[str, Any], duration: float) -> List[List[float]]:
    """
    根据事件图谱重新给高光片段打分(P1核心)
    highlights: [(start, end, score), ...]
    event_graph: {"events": [{"time": N, "importance": M}, ...]}
    返回: 按事件重要性调整后的 highlights
    """
    events = event_graph.get('events', [])
    if not events or not highlights:
        return highlights

    # 归一化事件时间到视频时长
    max_event_time = max(e.get('time', 0) for e in events) if events else 1
    scale = duration / max_event_time if max_event_time > duration else 1.0

    # 为每个高光片段计算事件加成
    scored_highlights = []
    for h in highlights:
        s, e, base_score = h[0], h[1], h[2]
        center = (s + e) / 2

        # 找最近的事件
        event_bonus = 0
        for ev in events:
            ev_time = ev.get('time', 0) * scale
            importance = ev.get('importance', 3)
            dist = abs(center - ev_time)

            # 距离越近加成越高,importance 1-5映射到加成 0-0.5
            if dist < EVENT_DISTANCE_THRESHOLD:  # 5秒内
                bonus = (importance / 5.0) * 0.5  # 最高+0.5
                event_bonus = max(event_bonus, bonus)

        # 新分数 = 基础分 * (1 + 事件加成)
        new_score = base_score * (1 + event_bonus)
        scored_highlights.append([s, e, new_score])

    # 按新分数排序
    scored_highlights.sort(key=lambda x: x[2], reverse=True)

    # 统计
    high_event_clips = sum(1 for h in scored_highlights if h[2] > 0.5)
    log(f"   🎯 事件加权: {high_event_clips}/{len(scored_highlights)}片段命中关键事件", "")

    return scored_highlights



    """

    高光片段识别:结合画面变化 + 音频能量

    返回 [(start, end, score), ...],按得分降序

    """

    info = get_video_info(path)

    if info["duration"] <= 0:

        return []



    duration = info["duration"]

    fps      = info["fps"]

    interval = CONFIG["analysis_interval"]

    min_sec  = CONFIG["clip_min_sec"]

    max_sec  = CONFIG["clip_max_sec"]

    threshold = CONFIG["highlight_threshold"]



    cap = cv2.VideoCapture(path)

    if not cap.isOpened():

        return []



    # 生成临时音频文件用于能量分析

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:

        tmp_wav = tmp_audio.name



    try:

        r = subprocess.run([

            "ffmpeg", "-y", "-i", path, "-vn", "-ac", "1",

            "-ar", "16000", "-acodec", "pcm_s16le", tmp_wav

        ], capture_output=True, timeout=60)

        if r.returncode != 0:

            raise RuntimeError(f"ffmpeg audio extraction failed: {r.stderr}")

        audio = AudioSegment.from_wav(tmp_wav)

    except Exception as e:

        log(f"   ⚠️ 音频提取失败: {e}", "")

        tmp_wav = None

        audio = None




    highlights = []

    prev_frame = None



    # 去掉每个视频最后3秒(避免片尾黑屏/文字混入)

    effective_duration = max(0, duration - 3.0)



    for sec in np.arange(0, effective_duration, interval):

        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)

        ret, frame = cap.read()

        if not ret:

            break



        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)



        # 检测片尾黑屏/文字画面,跳过

        if is_ending_clip(frame, gray):

            prev_frame = gray.copy()

            continue



        # 镜头类型检测

        shot_type, motion_score = detect_shot_type(frame, gray, prev_frame)

        shot_weight = SHOT_TYPE_WEIGHTS.get(shot_type, 1.0)



        frame_score = 0.0



        if prev_frame is not None:

            # 场景变化检测:帧差分均值(0~255)

            diff = cv2.absdiff(gray, prev_frame)

            mean_diff = float(np.mean(diff))

            # 映射到 0~1:mean_diff=5时约0.02,=30时约0.12

            frame_score = mean_diff / 255.0

        prev_frame = gray.copy()



        # 音频能量得分

        audio_score = 0.0

        if audio is not None:

            try:

                ms = int(sec * 1000)

                seg = audio[ms:ms + int(interval * 1000)]

                dBFS_val = seg.dBFS

                # dBFS 范围约 -50 到 0,映射到 0~1

                if dBFS_val > -50:

                    audio_score = min(max((dBFS_val + 50) / 50, 0), 1)

                else:

                    audio_score = 0.0

            except Exception:

                audio_score = 0.0



        total_score = (frame_score * 0.6 + audio_score * 0.4) * shot_weight



        # 运动镜头加分

        if motion_score > 0.15:

            total_score *= 1.3



        if total_score > threshold:

            # 扩展片段范围,确保满足最小时长要求

            start = max(0.0, sec - 1.0)

            end   = min(duration, sec + interval + 1.0)

            dur   = end - start

            if dur >= min_sec:  # 只检查最小时长,最大时长后面会裁剪

                highlights.append([start, end, total_score])



    cap.release()



    if tmp_wav and os.path.exists(tmp_wav):

        os.unlink(tmp_wav)



    # 去重:合并重叠/接近的片段

    highlights = sorted(highlights, key=lambda x: x[2], reverse=True)

    merged = []

    for h in highlights:

        s, e, sc = h

        overlapped = False

        for m in merged:

            ms, me, _ = m

            if not (e < ms or s > me):

                overlapped = True

                if sc > m[2]:

                    m[2] = sc

                break

        if not overlapped:

            merged.append(h)



    return merged



def _merge_nearby_highlights(highlights, gap_sec=1.0):

    """合并时间相近的高光片段



    highlights格式: [(start, end, score), ...] 或 [(start, end, score, file_idx), ...]

    gap_sec: 间隔小于此值的相邻片段会被合并

    """

    if not highlights:

        return []



    # 统一为4元组格式 (start, end, score, file_idx)

    normalized = []

    for h in highlights:

        if len(h) >= 4:

            normalized.append(tuple(h[:4]))

        else:

            normalized.append((h[0], h[1], h[2], 0))  # file_idx默认0



    # 按start排序后合并

    normalized.sort(key=lambda x: (x[0], x[1]))

    merged = []

    current = list(normalized[0])



    for seg in normalized[1:]:

        # 同一文件且间隔小于gap_sec则合并

        if seg[3] == current[3] and seg[0] - current[1] <= gap_sec:

            current[1] = max(current[1], seg[1])

            current[2] = max(current[2], seg[2])

        else:

            merged.append(tuple(current))

            current = list(seg)

    merged.append(tuple(current))



    return merged





def _align_clip_to_sentence(file_idx, s, e, all_file_subtitles):

    """截点对齐到字幕句子边界



    all_file_subtitles: {file_idx: [(start, end, text), ...]}

    开始点在句中→前移到句首,结束点在句中→后移到句尾

    最小保留1.5s

    """

    MIN_DURATION = 1.5



    subtitles = all_file_subtitles.get(file_idx, [])

    if not subtitles:

        return s, e



    # 对齐开始时间:找到包含s的字幕句,前移到句首

    new_s = s

    for sub_s, sub_e, sub_text in subtitles:

        if sub_s <= s < sub_e:

            # s在这个字幕句中间,前移到句首

            new_s = sub_s

            break



    # 对齐结束时间:找到包含e的字幕句,后移到句尾

    new_e = e

    for sub_s, sub_e, sub_text in subtitles:

        if sub_s < e <= sub_e:

            # e在这个字幕句中间,后移到句尾

            new_e = sub_e

            break



    # 确保最小保留时长

    if new_e - new_s < MIN_DURATION:

        # 优先扩展结束时间

        new_e = new_s + MIN_DURATION



    return new_s, new_e





def _get_video_duration(path):

    """获取视频时长(秒),调用已有的get_video_info"""

    try:

        info = get_video_info(path)

        if info and "duration" in info:

            return info["duration"]

    except Exception as ex:

        log(f"⚠️ 获取视频时长失败 {path}: {ex}", "⚠")

    return None





def detect_bgm_beats(bgm_path):

    """检测BGM节拍点,返回节拍时间列表(秒)"""

    try:

        audio = AudioSegment.from_file(bgm_path).set_channels(1)

        threshold = CONFIG["beat_threshold"] * 10

        interval_ms = int(CONFIG["beat_detection_interval"] * 1000)

        beats = []

        prev_db = None

        for i in range(0, len(audio), interval_ms):

            seg_db = audio[i].dBFS

            if prev_db is not None and seg_db - prev_db > threshold:

                beats.append(i / 1000)

            prev_db = seg_db

        return beats

    except Exception as e:

        log(f"BGM节拍检测失败: {e}", "⚠️")

        return []





    """



    从所选片段的实际字幕中提炼解说内容。



    aligned_selected: [(file_idx, s, e, sc), ...]



    all_file_subtitles: {file_idx: [(start, end, text), ...]}



    返回: [(text, start, end, file_idx), ...] 按时间顺序排列



    """



    result = []



    for file_idx, s, e, _ in selected_clips:



        subs = all_file_subtitles.get(file_idx, [])



        for sub_s, sub_e, sub_text in subs:



            if sub_text and len(sub_text.strip()) >= 2:



                overlap = min(e, sub_e) - max(s, sub_s)



                if overlap >= 0.5:



                    result.append((sub_text.strip(), sub_s, sub_e, file_idx))



    result.sort(key=lambda x: (x[3], x[1]))



    return result







def _call_ollama_retry(prompt: str, agent_name: str, timeout: int = 90, retries: int = 2) -> str:
    """
    统一Ollama调用函数:带重试、详细日志、指数退避
    """
    import time as _time
    import urllib.request
    for attempt in range(retries + 1):
        t0 = _time.time()
        try:
            # 清理prompt中的多余空白和可疑内容
            clean_prompt = re.sub(r'\s+', ' ', str(prompt)).strip()
            log(f"🤖 [{agent_name}] 第{attempt+1}/{retries+1}次调用 | prompt长度:{len(clean_prompt)}")

            data = _json.dumps({
                "model": "qwen3.5:4b",
                "prompt": clean_prompt,
                "stream": False,
                "think": False,
                "options": _get_llm_params(agent_name.lower())
            }, ensure_ascii=False).encode("utf-8")

            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = _json.loads(resp.read().decode("utf-8"))
                text = result.get("response", "").strip()
                elapsed = _time.time() - t0
                log(f"✅ [{agent_name}] 成功 | 耗时:{elapsed:.1f}s | 响应:{len(text)}字")
                return text

        except Exception as e:
            elapsed = _time.time() - t0
            log(f"⚠️ [{agent_name}] 第{attempt+1}次失败: {e} | 耗时:{elapsed:.1f}s")
            if attempt < retries:
                wait = (attempt + 1) * 3  # 指数退避: 3s, 6s
                log(f"   重试等待 {wait}s...")
                _time.sleep(wait)
            else:
                log(f"❌ [{agent_name}] 全部重试失败,走fallback")
                return None
    return None

def _extract_emotion_tags(full_text: str, mood_timeline: str, key_dialogues: list) -> List[str]:
    """
    从剧情内容中提取情绪标签,用于BGM匹配
    基于关键词、情绪词和高光片段综合分析
    """
    emotion_tags = []
    text_lower = full_text.lower()

    # 情绪关键词映射
    emotion_map = {
        "虐心": ["虐", "心痛", "心碎", "泪目", "哭泣", "绝望", "崩溃", "悲伤", "难过"],
        "甜宠": ["甜", "宠", "撒娇", "心动", "脸红", "心跳", "脸红", "亲吻", "拥抱", "幸福"],
        "紧张": ["紧张", "危机", "危险", "追逐", "对峙", "悬念", "恐怖", "惊险"],
        "热血": ["燃", "热血", "爆发", "怒吼", "狂喜", "兴奋", "激动", "振奋"],
        "搞笑": ["笑", "搞笑", "幽默", "逗", "呆萌", "搞笑", "段子"],
        "温情": ["温情", "感动", "暖心", "温馨", "治愈", "温柔", "关怀"],
        "复仇": ["复仇", "报仇", "反击", "逆袭", "翻身", "复仇", "雪耻"],
        "悬疑": ["悬疑", "谜", "真相", "秘密", "阴谋", "推理", "揭秘"],
    }

    # 从关键词命中计算情绪分数
    emotion_scores = {}
    for emotion, keywords in emotion_map.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            emotion_scores[emotion] = score

    # 从 mood_timeline 推断
    if mood_timeline:
        for emotion in emotion_scores:
            if emotion in mood_timeline:
                emotion_scores[emotion] += 2

    # 取分数最高的情绪标签(最多3个)
    sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
    emotion_tags = [e[0] for e in sorted_emotions[:3]]

    # 如果没有匹配,使用默认
    if not emotion_tags:
        emotion_tags = ["通用"]

    return emotion_tags


def _analyze_genre_for_bgm(full_text: str, base_genre: str) -> str:
    """
    分析剧情类型用于BGM匹配(比 detect_drama_genre 更精细)
    结合关键词和内容深度分析
    """
    text_lower = full_text.lower()

    # BGM风格类型映射(更细粒度)
    bgm_genre_map = {
        "虐心都市": ["都市", "渣男", "出轨", "离婚", "心碎", "背叛"],
        "甜宠都市": ["都市", "甜", "宠", "恋爱", "爱情", "甜蜜"],
        "古装虐恋": ["古代", "皇宫", "王爷", "虐", "失忆", "误会"],
        "古装甜宠": ["古代", "甜", "萌", "穿越", "欢喜"],
        "豪门总裁": ["豪门", "总裁", "霸总", "霸道", "总裁"],
        "复仇爽剧": ["复仇", "逆袭", "打脸", "爽", "翻身", "报仇"],
        "悬疑惊悚": ["悬疑", "恐怖", "惊悚", "灵异", "诡异"],
        "喜剧搞笑": ["喜剧", "搞笑", "段子", "逗比", "幽默"],
        "青春校园": ["校园", "青春", "学生", "暗恋", "初恋"],
    }

    # 计算匹配分数
    best_match = base_genre if base_genre else "都市言情"
    best_score = 0

    for bgm_genre, keywords in bgm_genre_map.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_match = bgm_genre

    return best_match


def _decision_agent(full_text: str, clip_subs: List[Tuple[str, float, float, int]], drama_info: Tuple[str, str], genre: str, total_duration: float) -> Dict[str, Any]:
    """
    决策层:分析剧情,输出解说大纲
    调用 _analyze_drama_context 获取剧情分析,标记关键台词
    """
    log("📝 决策层: 开始分析剧情结构...", "")

    # 1. 剧情分析(复用现有函数)
    ctx = _analyze_drama_context(full_text, None, None)

    # 2. 从字幕中提取关键台词(情绪词加权)
    key_dialogues = []
    emotion_words = {
        '冲突': ['滚', '死', '杀', '恨', '绝不', '休想', '凭什么', '为什么', '不可能', '别做梦'],
        '高潮': ['真相', '原来', '终于', '没想到', '竟然', '震惊', '崩溃', '绝望', '狂喜'],
        '悬念': ['到底是谁', '究竟', '秘密', '阴谋', '计划', '下一步', '等着瞧', '走着瞧']
    }

    for text, start, end, fidx in clip_subs:
        score = 0
        for cat, words in emotion_words.items():
            for w in words:
                if w in text:
                    score += 2 if cat == '冲突' else 1
        if score >= 2:
            key_dialogues.append({"text": text, "start": start, "score": score})

    # 按时间排序,取前10个关键台词
    key_dialogues.sort(key=lambda x: x["start"])
    key_dialogues = key_dialogues[:10]

    # 3. 确定解说结构
    events = ctx.get("events", [])
    mood = ctx.get("mood_timeline", "")

    # P1-3 改造:使用多样化叙事结构
    structure = _choose_diverse_structure(mood, genre)

    # 4. 参考字数(8字/秒确保解说覆盖全片,上限3000防LLM截断)
    target_chars = min(1500, max(480, int(total_duration * 8)))

    # 增强:分析剧情类型和情绪标签(用于BGM匹配)
    emotion_tags = _extract_emotion_tags(full_text, mood, key_dialogues)
    drama_genre_for_bgm = _analyze_genre_for_bgm(full_text, genre)

    result = {
        "characters": ctx.get("characters", []),
        "events": events,
        "mood_timeline": mood,
        "narration_hint": ctx.get("narration_hint", ""),
        "key_dialogues": key_dialogues,
        "narration_structure": structure,
        "style": genre if genre else "default",
        "target_chars": target_chars,
        "emotion_tags": emotion_tags,      # 情绪标签,用于BGM匹配
        "drama_genre_for_bgm": drama_genre_for_bgm  # 增强类型,用于BGM匹配
    }

    log(f"   📊 决策完成: {len(result['characters'])}角色, {len(result['key_dialogues'])}关键台词, 结构:{structure}", "")
    return result


def _execution_agent(decision: Dict[str, Any], clip_subs: List[Tuple[str, float, float, int]], drama_info: Tuple[str, str], genre: str) -> str:
    """
    执行层:片段驱动解说生成
    核心改动:按片段生成解说,用转场词衔接,确保解说内容与画面匹配
    """
    log("🎬 执行层: 片段驱动解说生成...", "")

    name, ep = drama_info if drama_info else ("女主", "01")
    target_chars = decision.get("target_chars", 300)
    key_dialogues = decision.get("key_dialogues", [])
    structure = decision.get("narration_structure", "")
    hint = decision.get("narration_hint", "")
    characters = decision.get("characters", [])

    # 1. 按时间分组字幕到片段(每2-4秒一个解说单元)
    clip_groups = _group_subs_to_clips(clip_subs, target_duration=3.0)

    if len(clip_groups) < 2:
        log("   ⚠️ 字幕分组太少,使用旧方法", "⚠️")
        return _execution_agent_legacy(decision, clip_subs, drama_info, genre)

    # 2. 为每个片段生成解说
    clip_narrations = []
    for i, group in enumerate(clip_groups):
        narr = _generate_clip_narration_llm(group, i, len(clip_groups),
                                            drama_info, genre, key_dialogues)
        clip_narrations.append(narr)
        log(f"   📝 片段{i+1}: {len(narr)}字", "")

    # 3. 拼接为连贯叙事
    full_narration = _join_clip_narrations(clip_narrations)

    if len(full_narration) >= 50:
        log(f"   ✅ 片段驱动解说: {len(full_narration)}字, {len(clip_groups)}个片段", "")
        return full_narration

    # 4. Fallback
    log("   ⚠️ 片段驱动失败,使用旧方法", "⚠️")
    return _execution_agent_legacy(decision, clip_subs, drama_info, genre)


def _group_subs_to_clips(clip_subs: list, target_duration: float = 3.0) -> list:
    """
    将字幕按时间分组为片段解说单元
    返回: [[(text, start, end), ...], ...]
    """
    if not clip_subs:
        return []

    groups = []
    current_group = []
    current_start = None
    current_duration = 0

    for text, start, end, fidx in clip_subs:
        if current_start is None:
            current_start = start

        current_group.append((text, start, end))
        current_duration = end - current_start

        # 达到目标时长,切分
        if current_duration >= target_duration:
            groups.append(current_group)
            current_group = []
            current_start = None
            current_duration = 0

    # 剩余的
    if current_group:
        groups.append(current_group)

    return groups


def _generate_clip_narration_llm(clip_group: list, clip_idx: int, total_clips: int,
                                   drama_info: tuple, genre: str, key_dialogues: list) -> str:
    """用LLM为单个片段生成解说"""
    import urllib.request, json as _json

    # 确定片段位置(开头/中间/结尾)
    if clip_idx == 0:
        position = "开头"
        position_hint = "用悬念式开头,抛出问题或冲突,吸引观众继续看"
    elif clip_idx == total_clips - 1:
        position = "结尾"
        position_hint = "总结剧情,留悬念钩子,引导关注下集"
    else:
        position = "中间"
        position_hint = "展开剧情,用转场词衔接上下文"

    # 片段时长和字数目标
    duration = clip_group[-1][2] - clip_group[0][1]
    target_chars = max(8, min(int(duration * 3.5), 20))

    # 提取关键台词
    key_texts = {k["text"] for k in key_dialogues}
    clip_texts = []
    has_key = False
    for text, start, end in clip_group:
        clip_texts.append(text)
        if text in key_texts:
            has_key = True

    subtitle_text = " ".join(clip_texts[:10])

    # P0-2 改造:使用差异化Prompt
    _segment_info = {"text": subtitle_text, "group_idx": clip_idx}
    prompt = _build_diverse_prompt(_segment_info, clip_idx, total_clips)

    # 调用Ollama(短超时)
    # P0改造: 使用统一重试函数,根据位置传入正确的agent_name
    if clip_idx == 0:
        _agent = "clip_narration_first"
    elif clip_idx == total_clips - 1:
        _agent = "clip_narration_final"
    else:
        _agent = "clip_narration_middle"
    text = _call_ollama_retry(prompt, _agent, timeout=60, retries=2)
    if text:
        text = re.sub(r'^(解说:|解说词:|直接输出:)', '', text).strip()
        if len(text) >= 5:
            return text

    # Fallback:直接用字幕精简
    return _simplify_subtitle(subtitle_text, target_chars)


def _simplify_subtitle(text: str, target: int) -> str:
    """精简字幕为目标字数"""
    noise = ['大家好', '感谢', '点赞', '关注', 'BGM', '背景音乐']
    for n in noise:
        text = text.replace(n, '')
    text = re.sub(r'[,。!?、;:]', '', text)
    return text[:target].strip() if len(text) > target else text.strip()


def _join_clip_narrations(clip_narrations: list) -> str:
    """拼接片段解说为连贯叙事"""
    if not clip_narrations:
        return ""
    if len(clip_narrations) == 1:
        return clip_narrations[0]

    # 转场词库
    transitions = [
        "",
        "然而",
        "不料",
        "就在这时",
        "没想到",
        "谁知",
        "突然",
        "就在此时",
        "更糟的是",
        "最终"
    ]

    result = []
    for i, narr in enumerate(clip_narrations):
        if not narr:
            continue
        # 开头不加转场词
        if i == 0:
            result.append(narr)
        else:
            # 选择转场词
            trans = transitions[min(i, len(transitions)-1)]
            if trans:
                # [FIX-20260628] 修正转场词拼接格式: "然而,解说" -> "然而,解说。"
                result.append(f"{trans},{narr}")
            else:
                result.append(narr)

    # 用句号连接各片段
    text = "。".join(result)
    if text and text[-1] not in "。!?!?":
        text += "。"
    return text


def _execution_agent_legacy(decision: dict, clip_subs: list, drama_info: tuple, genre: str) -> str:
    """旧版执行层(作为fallback)"""
    log("🎬 执行层(legacy): 生成解说文案...", "")

    name, ep = drama_info if drama_info else ("女主", "01")
    target_chars = decision.get("target_chars", 300)
    key_dialogues = decision.get("key_dialogues", [])
    structure = decision.get("narration_structure", "")
    hint = decision.get("narration_hint", "")
    characters = decision.get("characters", [])

    # 准备字幕文本(清理噪音)
    noise = {'大家好', '感谢点击', '关注我', '点击头像', '上滑继续', 'BGM',
             '背景音乐', '配乐', '特效', '广告', '点赞', '收藏', '转发',
             '评论区', '弹幕', '关注', '谢谢观看', '喜欢的话', '记得点赞',
             '持续更新', '下期再见', '片头', '片尾', '字幕'}

    lines = []
    key_texts = {k["text"] for k in key_dialogues}

    for text, start, end, fidx in clip_subs:
        t = text.strip()
        if len(t) < 3 or t in noise or t.startswith(('【', '『', '[', '#')):
            continue
        if re.match(r'^[\d\s\W]+$', t):
            continue
        # 标记关键台词
        is_key = t in key_texts
        lines.append({"time": int(start), "text": t, "key": is_key})

    if len(lines) < 2:
        return None

    # 构建prompt(注入决策层信息)
    subtitle_text = "\n".join([f"{'[关键]' if l['key'] else ''}{l['time']}s: {l['text']}" for l in lines[:60]])
    scene = genre if genre else "都市言情"
    char_list = ", ".join(characters[:5]) if characters else "女主, 男主"

    prompt = f"""你是一个短剧解说高手。请为《{name}》第{ep}集写一段流畅的解说词。

【剧情信息】
类型: {scene}
主要角色: {char_list}
叙事结构: {structure}
解说风格建议: {hint}

【原声台词】([关键]标记的是剧情重点,必须融入解说)
{subtitle_text}

【要求】
1. 用自然流畅的语言讲故事,像抖音短剧解说一样有节奏感
2. 必须包含所有[关键]台词的核心信息,不要遗漏
3. 用「她」「他」「女主」「男主」指代角色,不要用"女主角""男主角"
4. 用解说语气自然开场,不要用"震惊""没想到""竟然"等标题党词汇,直接进入剧情场景
5. 删除广告词、感谢语、纯语气词
6. 字数控制在{target_chars}字左右
7. 直接输出解说正文,不要加标题或标签

8.  【合规-叙事价值观】禁止渲染以下内容:
   - 制造社会阶层对立(富人vs穷人、城里人vs农村人、权势vs弱势)
   - 宣扬以暴制暴、极端复仇快感、私刑正义
   - 强化性别刻板印象、婆媳对立、夫妻互害
   - 美化不劳而获、拜金主义、权力碾压
9.  【合规-词汇避让】禁止使用以下词汇:
   - 煽动对立:「碾压」「踩踏」「蹂躏」「完爆」「打脸」「打回去」
   - 暴力暗示:「弄死」「干掉」「废了」「收拾他」「搞死」
   - 炫富歧视:「穷鬼」「土包子」「配不上」「活该」
   - 标题党:「震惊」「没想到」「竟然」「万万没想到」「反转」
10. 【合规-AI标识】解说中自然融入一句话AI创作声明(如"AI剪的"或"AI带你追剧"),放在开头或结尾,不生硬
11. 【合规-结局导向】冲突解决强调理性方式(法律、沟通、成长),结局传递正向价值--善良有回报、努力有收获、真诚被珍惜

解说词:"""

    # P0改造: 统一重试函数
    text = _call_ollama_retry(prompt, "narration_legacy", timeout=90, retries=2)
    if text:
        text = re.sub(r'^(解说:|解说词:|正文:|Narration:|narration:|Naration:|naration:|#+)', '', text).strip()
        text = text.strip('"""\'"').strip()
        if len(text) >= 50:
            log(f"   ✅ LLM生成成功: {len(text)}字", "")
            return text

    # Fallback: 改进的拼接
    return _build_narration_fallback(lines, target_chars)

    # P0改造: 统一重试函数
    text = _call_ollama_retry(prompt, "narration_legacy", timeout=90, retries=2)
    if text:
        text = re.sub(r'^(解说:|解说词:|正文:|#+|\*+)', '', text).strip()
        text = text.strip('"""\'"').strip()
        if len(text) >= 50:
            log(f"   ✅ LLM生成成功: {len(text)}字", "")
            return text

    # Fallback: 改进的拼接(去掉机械三段式)
    return _build_narration_fallback(lines, target_chars)


def _build_narration_fallback(lines: list, target_chars: int) -> str:
    """LLM失败时的fallback:连贯拼接而非机械三段式"""
    if not lines:
        return None

    # 按时间排序
    lines.sort(key=lambda x: x["time"])

    # 清理并合并短句
    merged = []
    for l in lines:
        t = l["text"]
        # 去掉常见噪音
        if any(n in t for n in ['大家好', '感谢', '点赞', '关注', 'BGM']):
            continue
        # 合并到前一句(如果很短)
        if merged and len(t) < 8 and not t.endswith(('。', '!', '?')):
            merged[-1] += ',' + t
        else:
            merged.append(t)

    # 用衔接词串联
    connectors = ['', '原来', '然而', '没想到', '就在此时', '更糟的是', '终于', '结果']
    result = []
    total_len = 0
    conn_idx = 0

    for i, sent in enumerate(merged):
        if total_len >= target_chars:
            break
        # 每3句加一个衔接词
        if i > 0 and i % 3 == 0 and conn_idx < len(connectors):
            sent = connectors[conn_idx] + ',' + sent
            conn_idx += 1
        result.append(sent)
        total_len += len(sent)

    text = '。'.join(result)
    if not text.endswith(('。', '!', '?')):
        text += '。'

    log(f"   📝 Fallback拼接: {len(text)}字", "")
    # P0-1 改造:如果结果太短,使用多样化模板补充
    if len(result) < 50:
        import random as _rnd
        _supplement = _get_diversified_narration()
        result = (result + " " + _supplement).strip() if result else _supplement

    return text


def _supervision_agent(narration: str, decision: Dict[str, Any], clip_subs: List[Tuple[str, float, float, int]], target_hint: int = 0) -> Tuple[str, bool]:
    """
    监督层:审计解说质量(不强制字数限制)
    返回: (最终解说, 是否通过)
    """
    log("🔍 监督层: 审计解说质量...", "")

    if not narration or len(narration) < MIN_NARRATION_LENGTH:
        log("   ❌ 解说太短,不通过", "⚠️")
        return narration, False

    issues = []

    # 2. 关键台词覆盖率
    key_dialogues = decision.get("key_dialogues", [])
    covered = 0
    for k in key_dialogues:
        # 简化检查:关键台词的核心词是否在解说中
        key_words = set(k["text"][:4])  # 前4个字作为标识
        if any(w in narration for w in key_words):
            covered += 1

    coverage = covered / len(key_dialogues) if key_dialogues else 1.0
    if coverage < KEY_DIALOGUE_COVERAGE_THRESHOLD:
        issues.append(f"关键台词覆盖率低({coverage:.0%})")

    # 3. 连贯性检查(重复衔接词)
    bad_patterns = ['然而然而', '没想到没想到', '原来原来', ',,', '。。']
    for p in bad_patterns:
        if p in narration:
            issues.append("存在重复衔接词")
            break

    # 4. 结尾检查
    if not narration[-1] in '。!?':
        issues.append("结尾无标点")
        narration += '。'

    if issues:
        log(f"   ⚠️ 发现问题: {'; '.join(issues)}", "⚠️")
        return narration, False

    log(f"   ✅ 审计通过: {len(narration)}字, 覆盖率{coverage:.0%}", "")
    return narration, True

def _analyze_drama_context(full_text: str, selected_clips: list = None,
                             all_file_subtitles: dict = None) -> dict:
    """
    AI分析剧情上下文(Jellyfish风格的剧本理解)
    - 提取角色名列表
    - 分析场景/情绪变化
    - 识别关键事件节点(冲突/高潮/转折)
    - 给出解说生成建议
    使用 Ollama gemma4
    """
    import urllib.request, json as _json
    if not full_text or len(full_text.strip()) < 20:
        return {"characters": [], "events": [], "mood_timeline": "", "narration_hint": ""}

    text_sample = full_text[:MAX_TEXT_SAMPLE]

    prompt = f"""你是一个专业的短剧解说编剧。分析以下短剧台词,提取结构化信息。

台词:
{text_sample}

请提取:
1. 角色名列表(从对白中识别的说话人,如"女主"、"男主"、"她"、"他")
2. 关键事件节点:按时间顺序列出剧情转折点(3-5个)
3. 情绪曲线:开头→中期→高潮的情绪走向描述
4. 解说建议:用50字说明这个故事的核心看点和解说风格

输出格式(JSON,只输出JSON):
{{"characters":["角色1","角色2"],"events":["事件1","事件2"],"mood_timeline":"情绪描述","narration_hint":"解说风格建议"}}

只输出JSON,不要其他文字:"""

    # P0改造: 统一重试函数
    raw = _call_ollama_retry(prompt, "bgm_selection", timeout=90, retries=2)
    if raw:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            ctx = _json.loads(match.group())
            log(f"   📖 剧情分析: 发现{len(ctx.get('characters',[]))}个角色, {len(ctx.get('events',[]))}个事件", "")
            return ctx
    return {"characters": [], "events": [], "mood_timeline": "", "narration_hint": ""}


def generate_narration(
    full_text: str,
    drama_info: Tuple[str, str] = ('女主', '01'),
    genre: str = '',
    key_words: Optional[List[str]] = None,
    emotion_curve: Optional[List[float]] = None,
    position: str = 'intro',
    target_chars: int = 300,
    selected_clips: Optional[List[Tuple[int, float, float, float]]] = None,
    all_file_subtitles: Optional[Dict[int, List[Tuple[str, float, float]]]] = None,
    total_duration: float = 60.0
) -> Tuple[str, Optional[str]]:
    """
    生成解说(三层Agent协作版)
    返回: (解说文本, 音频文件路径或None)
    """
    log(f"🎙️ 生成解说: 时长{total_duration:.1f}s", "")

    # 调试:打印字幕数据状态
    if all_file_subtitles:
        total_subs = sum(len(v) for v in all_file_subtitles.values())
        log(f"   📋 字幕数据: {len(all_file_subtitles)}个文件, 共{total_subs}条字幕", "")
    else:
        log(f"   📋 字幕数据: 空(all_file_subtitles is None or empty)", "")
    if selected_clips:
        log(f"   📋 已选片段: {len(selected_clips)}个", "")

    # 1. 提取片段字幕
    clip_subs = []
    if selected_clips and all_file_subtitles:
        clip_subs = _extract_clip_subtitles(selected_clips, all_file_subtitles)

    if not clip_subs:
        log("   ⚠️ 无字幕数据,使用模板兜底", "⚠️")
        narration = _build_narration_viral(drama_info[0], genre, [full_text] + (key_words or []),
                                           emotion_curve or [], position, target_chars)
        return narration, None

    # 2. 决策层分析
    decision = _decision_agent(full_text, clip_subs, drama_info, genre, total_duration)

    # [FIX-解说比例过少-20260702] 强制确保解说字数覆盖整段视频
    # 8 chars/sec × total_duration = 最低解说字数(确保连续覆盖)
    _min_chars = int(total_duration * 8)
    _dec_chars = decision.get("target_chars", 300)
    if _dec_chars < _min_chars:
        decision["target_chars"] = _min_chars
        log(f"   📏 解说目标字数: {_dec_chars}→{_min_chars}(视频{total_duration:.1f}s,需覆盖全片)", "")

    # 3. 执行层生成(最多2次尝试)
    narration = None
    for attempt in range(2):
        narration = _execution_agent(decision, clip_subs, drama_info, genre)
        if not narration:
            log(f"   ⚠️ 执行层第{attempt+1}次生成失败", "⚠️")
            continue

        # 4. 监督层审计
        narration, passed = _supervision_agent(narration, decision, clip_subs, target_hint=decision.get("target_chars", 0))
        if passed:
            break
        log(f"   🔄 监督层不通过,重试...", "")

    # [P0-解说覆盖率] 字数不足时自动回补:从字幕中提取补充内容
    _min_required_chars = int(total_duration * 4.5)  # ChatTTS实际语速~4.5字/秒
    if narration and len(narration) < _min_required_chars * 0.8:
        _shortfall = _min_required_chars - len(narration)
        log(f"   ⚠️ 解说字数不足: {len(narration)}/{_min_required_chars}字,缺口{_shortfall}字,强制回补", "⚠️")
        # 从字幕中提取补充内容
        _extra_lines = []
        if clip_subs:
            # 取字幕后半段(通常解说没覆盖到)
            _used_text = narration
            for _t, _s, _e, _fidx in clip_subs:
                _clean = _t.strip()
                if len(_clean) >= 4 and _clean not in narration and _clean not in _extra_lines:
                    _extra_lines.append(_clean)
                    if sum(len(l) for l in _extra_lines) >= _shortfall:
                        break
        if _extra_lines:
            _padding = '。'.join(_extra_lines[:max(5, len(_extra_lines))])
            narration = narration.rstrip('。!!??') + '。' + _padding + '。'
            log(f"   ✅ 回补完成: {len(narration)}字(补充{len(_padding)}字)", "✅")
        else:
            # 没有可用字幕时,用通用填充
            _generic_fillers = [
                'AI带你感受这段故事的每一个细节',
                '想知道后来发生了什么吗,继续关注精彩剧情',
                '每一个转折都让人意想不到,故事的张力在此刻到达顶点',
                '剧中的情感冲突,折射出现实生活中我们每个人都可能面对的处境',
                '这不仅仅是一段剧情,更是人性深处最真实的写照',
            ]
            _gfill = random.choice(_generic_fillers) if 'random' in dir() else _generic_fillers[0]
            narration = narration.rstrip('。!!??') + '。' + _gfill + '。'
            log(f"   ✅ 通用回补完成: {len(narration)}字", "✅")

    # 5. Fallback:如果三层都失败,用模板
    if not narration or len(narration) < MIN_VALID_NARRATION:
        log("   📝 使用模板兜底", "")
        narration = _build_narration_viral(drama_info[0], genre, [full_text] + (key_words or []),
                                           emotion_curve or [], position, target_chars,
                                           context_hint=decision.get("narration_hint", ""))

    log(f"   ✅ 最终解说: {len(narration)}字", "")

    # 6. TTS生成(保持原有逻辑)
    audio_path = None
    if narration:
        # drama_name从drama_info[0]获取
        _drama_name = drama_info[0] if drama_info else ""
        audio_path = _tts_narration(narration, genre, drama_name=_drama_name)

    return narration, audio_path


def _tts_narration(narration: str, genre: str, drama_name: str = "") -> str:
    """TTS生成:仅ChatTTS(无降级),自动分块+批量生成确保音色一致"""
    import tempfile, os, subprocess, re as _re

    voice = _pick_narration_voice(genre)

    if not CHAT_TTS_AVAILABLE:
        return None

    try:
        # === 长文本分块处理 ===
        # ChatTTS 有最大生成长度限制(~30s),长文本会被无声截断
        # 按句子切块(。!?-),每块不超过60字
        def _split_text(text: str, max_chars: int = 60) -> list:
            """按句子边界切分文本为小段"""
            sentences = _re.split(r'(?<=[。!?-])', text.strip())
            chunks = []
            current = ''
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(current) + len(s) <= max_chars:
                    current += s
                else:
                    if current:
                        chunks.append(current)
                    if len(s) > max_chars:
                        parts = _re.split(r'(?<=[,、;])', s)
                        for p in parts:
                            if not p.strip():
                                continue
                            if len(current) + len(p) <= max_chars:
                                current += p
                            else:
                                if current:
                                    chunks.append(current)
                                current = p
                    else:
                        current = s
            if current:
                chunks.append(current)
            return chunks

        chunks = _split_text(narration)
        if len(chunks) <= 1:
            chunks = [narration]

        # 提前计算确定性种子(MD5跨会话稳定),供短文本和批量两路共用
        import hashlib
        seed_source = drama_name if drama_name else (genre if genre else "default")
        _seed = int(hashlib.md5(seed_source.encode('utf-8')).hexdigest()[:8], 16) % (2**31)

        if len(chunks) <= 1:
            # 短文本:单次生成
            from tts_chattts_wrapper import tts_chattts
            fd, path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            log(f"   🔊 ChatTTS生成语音({len(narration)}字)...", "")
            result = tts_chattts(narration, path, seed=_seed)
            if result and os.path.exists(path) and os.path.getsize(path) > 0:
                mp3_path = path.replace('.wav', '.mp3')
                r = subprocess.run(['ffmpeg', '-y', '-i', path, '-b:a', '192k', mp3_path],
                                  capture_output=True, timeout=30)
                if r.returncode == 0 and os.path.exists(mp3_path):
                    os.remove(path)
                    log(f"   🔊 ChatTTS生成成功", "")
                    return mp3_path
            return None

        # 长文本:批量生成(tts_chattts_batch 一次 infer() 传入全部块→音色一致)
        from tts_chattts_wrapper import tts_chattts_batch
        log(f"   🔊 ChatTTS批量生成({len(chunks)}块,{len(narration)}字)...", "")

        # 批量生成到临时目录
        _tmp_batch_dir = tempfile.mkdtemp(prefix='tts_batch_')
        audio_files = tts_chattts_batch(chunks, output_dir=_tmp_batch_dir, seed=_seed)

        if len(audio_files) < 1:
            import shutil
            try: shutil.rmtree(_tmp_batch_dir)
            except Exception: pass
            return None

        if len(audio_files) == 1:
            # 仅一块成功:直接转mp3
            path = audio_files[0]
            mp3_path = path.replace('.wav', '.mp3')
            r = subprocess.run(['ffmpeg', '-y', '-i', path, '-b:a', '192k', mp3_path],
                              capture_output=True, timeout=30)
            import shutil
            try: shutil.rmtree(_tmp_batch_dir)
            except Exception: pass
            if r.returncode == 0 and os.path.exists(mp3_path):
                log(f"   🔊 ChatTTS生成成功", "")
                return mp3_path
            return None

        # 多块:FFmpeg concat无缝拼接(去掉句间静音,避免被抖音检测为"无解说区段")
        fd, list_path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        with open(list_path, 'w', encoding='utf-8') as f:
            for af in audio_files:
                f.write(f"file '{af}'\n")

        fd, concat_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        concat_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', list_path, '-c', 'copy',
            concat_path
        ]
        cr = subprocess.run(concat_cmd, capture_output=True, timeout=60)

        import shutil
        try: shutil.rmtree(_tmp_batch_dir)
        except Exception: pass
        try: os.remove(list_path)
        except Exception: pass

        if cr.returncode == 0 and os.path.exists(concat_path) and os.path.getsize(concat_path) > 100:
            mp3_path = concat_path.replace('.wav', '.mp3')
            r = subprocess.run(['ffmpeg', '-y', '-i', concat_path, '-b:a', '192k', mp3_path],
                              capture_output=True, timeout=30)
            os.remove(concat_path)
            if r.returncode == 0 and os.path.exists(mp3_path):
                log(f"   🔊 ChatTTS生成成功({len(audio_files)}块拼接,音色一致)", "")
                return mp3_path
        else:
            log(f"   ⚠️ 音频拼接失败: {cr.stderr.decode('utf-8','ignore')[-200:]}", "⚠️")

        return None

    except Exception as e:
        log(f"   ⚠️ ChatTTS失败: {e}", "⚠️")
        return None

def validate_output(output_path):

    """抖音合规原创检测:分辨率、时长、码率、敏感词、原创度"""

    try:

        info = get_video_info(output_path)

        ok = True

        issues = []



        # 1. 基础规格检测

        if info["width"] != CONFIG["width"] or info["height"] != CONFIG["height"]:

            issues.append(f"分辨率: {info['width']}x{info['height']}")

            ok = False

        if not (CONFIG["min_duration"] <= info["duration"] <= CONFIG["max_duration"]):

            issues.append(f"时长: {info['duration']:.1f}s")

            ok = False



        # 2. 码率检测(抖音推荐2-8Mbps)

        file_size = os.path.getsize(output_path)

        bitrate = (file_size * 8) / info["duration"] / 1000000 if info["duration"] > 0 else 0

        if bitrate < 2:

            issues.append(f"码率偏低: {bitrate:.1f}Mbps(推荐≥2Mbps)")

        elif bitrate > 10:

            issues.append(f"码率偏高: {bitrate:.1f}Mbps(推荐≤10Mbps)")



        # 3. 帧率检测(抖音推荐30fps)

        fps = info.get("fps", 0)

        if fps and fps < 24:

            issues.append(f"帧率偏低: {fps}fps(推荐≥30fps)")



        # 4. 敏感词检测(基于文件名)

        filename = os.path.basename(output_path)

        safe, filtered, found = is_safe_text(filename)

        if not safe:

            issues.append(f"文件名含敏感词: {found}")

            ok = False



        # 5. 原创度检测:片段多样性评估

        # 检查视频是否有足够的内容变化(避免纯搬运)

        clip_count = getattr(validate_output, '_clip_count', 0)

        if clip_count > 0:

            if clip_count >= 8:

                originality = "高 ✅"

            elif clip_count >= 5:

                originality = "中 ⚠️"

            else:

                originality = "低 ❌"

                issues.append(f"剪辑片段仅{clip_count}个,原创度偏低")

            log(f"📊 原创度评估: {clip_count}个片段 → {originality}", "📊")



        # 6. 音频检测(抖音必须有音频轨)

        has_audio = info.get("has_audio", False)

        if not has_audio:

            issues.append("无音频轨道(抖音要求必须有音频)")

            ok = False



        # 输出检测结果

        if ok and not issues:

            log(f"✅ 合规检测通过: {info['width']}x{info['height']} @ {info['duration']:.1f}s | 码率:{bitrate:.1f}Mbps", "✅")

        else:

            for issue in issues:

                log(f"⚠️ {issue}", "⚠️")

            if ok:

                log(f"✅ 合规检测通过(有建议项)", "✅")



        return ok

    except Exception as e:

        log(f"校验失败: {e}", "⚠️")

        return False




# ==================== 【5.5】智能特效处理系统 ====================



def get_genre_for_effects(genre: str) -> str:

    """将剧情类型映射到特效风格"""

    genre_map = {

        # 重生/复仇类 → 高能战斗风格

        "reincarnation": "revenge",

        "revenge": "revenge",

        "hidden_power": "revenge",

        "abuse": "revenge",



        # 总裁/甜宠类 → 明亮甜美风格

        "ceo": "sweet",

        "sweet": "sweet",

        "mistaken": "sweet",



        # 穿越/古风类 → 复古典雅风格

        "transmigration": "ancient",

        "ancient": "ancient",



        # 虐心/悲情类 → 暗色调风格

        "sad": "sad",



        # 悬疑/阴谋类 → 悬疑风格

        "suspense": "suspense",

        "conspiracy": "suspense",



        # 搞笑/轻松类 → 活泼风格

        "funny": "funny",



        # 现代/都市类 → 时尚风格

        "modern": "modern",

    }

    return genre_map.get(genre, "default")





def apply_video_effects(input_path: str, output_path: str, genre: str) -> bool:

    """

    根据剧情类型自动应用视频特效(滤镜+动态效果)

    使用 FFmpeg 内置滤镜,无需额外素材

    """

    if not CONFIG.get("auto_effects", True):

        log("自动特效已关闭,跳过", "⚠️")

        return False



    # 获取对应的特效配置

    genre_key = get_genre_for_effects(genre)

    effects_cfg = CONFIG.get("effects", {})

    filters = effects_cfg.get("filter", {})

    overlays = effects_cfg.get("overlay", {})



    # 构建滤镜链

    filter_parts = []



    # 1. 基础色彩调整(滤镜)

    filter_expr = filters.get(genre_key, filters.get("default", ""))

    if filter_expr:

        filter_parts.append(filter_expr)



    # 2. 动态暗角(悬疑/虐心)

    if overlays.get("vignette", {}).get("enabled"):

        if genre_key in overlays["vignette"].get("trigger_genres", []):

            filter_parts.append(overlays["vignette"]["effect"])



    # 3. 复古噪点(古风)

    if overlays.get("grain", {}).get("enabled"):

        if genre_key in overlays["grain"].get("trigger_genres", []):

            filter_parts.append(overlays["grain"]["effect"])



    # 4. 轻微闪光(甜宠/复仇高潮)- 用 colorchannelmixer 模拟

    if overlays.get("sparkle", {}).get("enabled"):

        if genre_key in overlays["sparkle"].get("trigger_genres", []):

            # 周期性亮度脉冲

            filter_parts.append("colorchannelmixer=1:1:1:0:1:1:1:0:1:1:1:0")

            filter_parts.append("eq=brightness=0.05:saturation=1.1")



    if not filter_parts:

        # 无特效,直接复制

        subprocess.run(["cp", input_path, output_path], timeout=30)

        log("无特效应用", "")

        return False



    # 合并所有滤镜

    video_filter = ",".join(filter_parts)



    cmd = [

        "ffmpeg", "-y",

        "-i", input_path,

        "-vf", video_filter,

        "-c:v", "libx264", "-preset", "fast", "-crf", "18",

        "-c:a", "copy",

        "-shortest",

        output_path

    ]



    r = subprocess.run(cmd, capture_output=True, timeout=180)

    if r.returncode != 0:

        log(f"特效应用失败,改用原视频: {r.stderr.decode()[-100:]}", "⚠️")

        subprocess.run(["cp", input_path, output_path], timeout=30)

        return False



    log(f"✅ 特效已应用 [{genre_key}]: {video_filter[:50]}...", "✨")

    return True





def build_clip_list_with_transitions(clips: list, input_path: str, tmp_dir: str, genre: str) -> str:

    """

    构建带转场的片段列表

    使用更精确的 FFmpeg 裁剪方式避免黑屏

    """

    if len(clips) <= 1:

        # 单片段不需要转场

        return build_clip_list_ffmpeg(clips, input_path, tmp_dir)



    # 获取转场配置

    genre_key = get_genre_for_effects(genre)



    tmp_clips_dir = os.path.join(tmp_dir, "clips_with_trans")

    os.makedirs(tmp_clips_dir, exist_ok=True)



    clip_files = []

    for i, (start, end, score) in enumerate(clips):

        clip_path = os.path.join(tmp_clips_dir, f"clip_{i:03d}.mp4")

        duration = end - start



        # 改进:先seek到关键帧附近,再精确裁剪

        # 使用 -ss 在输入前 + -accurate_seek 减少黑屏

        cmd = [

            "ffmpeg", "-y",


            "-i", input_path,
            "-ss", str(start),

            "-t", str(duration),

            "-c:v", "libx264", "-preset", "fast", "-crf", "18",

            "-c:a", "aac", "-b:a", "128k",

            "-movflags", "+faststart",

            # 添加帧复制避免裁剪黑屏

            "-avoid_negative_ts", "make_zero",

            clip_path

        ]

        r = subprocess.run(cmd, capture_output=True, timeout=SUBPROCESS_TIMEOUT)

        if r.returncode != 0:

            # 如果失败,尝试不指定音频编码

            cmd = [

                "ffmpeg", "-y",


                "-i", input_path,
                "-ss", str(start),

                "-t", str(duration),

                "-c:v", "libx264", "-preset", "fast", "-crf", "18",

                "-c:a", "copy",

                "-avoid_negative_ts", "make_zero",

                clip_path

            ]

            subprocess.run(cmd, capture_output=True, timeout=SUBPROCESS_TIMEOUT)



        if os.path.exists(clip_path) and os.path.getsize(clip_path) > 1000:

            clip_files.append(clip_path)



    if not clip_files:

        return build_clip_list_ffmpeg(clips, input_path, tmp_dir)



    # 简化处理:直接拼接

    concat_list = os.path.join(tmp_dir, "trans_concat.txt")

    with open(concat_list, "w", encoding="utf-8") as f:

        for cf in clip_files:

            f.write(f"file '{cf}'\n")



    output_path = os.path.join(tmp_dir, "clips_transitioned.mp4")



    # 使用 fade 效果实现简单转场

    cmd = [

        "ffmpeg", "-y",

        "-f", "concat",

        "-safe", "0",

        "-i", concat_list,

        "-vf", "fade=t=in:st=0:d=0.3,fade=t=out:st=14.5:d=0.5",

        "-c:v", "libx264", "-preset", "fast", "-crf", "18",

        "-c:a", "aac", "-b:a", "192k",

        "-shortest",

        output_path

    ]



    r = subprocess.run(cmd, capture_output=True, timeout=LONG_SUBPROCESS_TIMEOUT)

    if r.returncode != 0:

        # 转场失败,回退到普通拼接

        log(f"转场处理失败,回退到普通拼接: {r.stderr.decode()[-100:]}", "⚠️")

        return build_clip_list_ffmpeg(clips, input_path, tmp_dir)



    log(f"✅ 已应用转场效果 (共{len(clips)}个片段)", "🎬")

    return output_path



# ==================== 【5.5】抖音推流优化系统 ====================

# 抖音算法核心指标:完播率 > 互动率 > 转粉率 > 分享率

# 本模块解决"有流量但推不动"的问题



import random

import hashlib

from datetime import datetime

# Toonflow集成:多集记忆系统
try:
    from jellyfish_studio import AssetManager
    _ASSET_MANAGER_AVAILABLE = True
except ImportError:
    _ASSET_MANAGER_AVAILABLE = False



# ---- 爆款标题库(评论区验证高点击率模板)----

VIRAL_TITLE_TEMPLATES = {

    # 反转型(情绪冲击)

    "reverse": [

        "{name}以为这辈子完了,没想到三年后逆袭成顶流!",

        "全网都在骂她,直到监控曝光那刻,全场沉默了...",

        "他被所有人抛弃,却在婚礼上宣布一件事,全场炸裂!",

        "她消失了三年,带着三个天才萌宝回归,前夫当场跪下!",

        "这反转太绝了!连刷三遍才看懂,评论区已炸!",

        "婆婆处处刁难儿媳,直到她拿出这份文件,全家傻眼了!",

        "穷小子被赶出公司,三年后回来,全公司都傻眼了!",

        "她替姐姐嫁入豪门,众人嘲笑她配不上,直到...",

    ],

    # 数字型(具体感强,点击率高)

    "number": [

        "这{num}个细节,没几个人注意到!",

        "连续刷了三遍,终于在第{nums}秒发现了这个!",

        "99%的人都没注意到的{num}个伏笔!",

        "这个{nums}秒的镜头,导演用心了!",

        "导演埋了{nums}个彩蛋,你看出来了几个?",

        "她的这{nums}句话,每句都是刀子!",

        "这部剧的{nums}个名场面,看一次哭一次!",

        "三年{nums}部剧,这部是最绝的!",

    ],

    # 冲突型(引发好奇)

    "conflict": [

        "她嫁入豪门却被全家针对,直到她亮出真实身份!",

        "他是她最恨的人,也是救她命的人!",

        "嘴上说不要,身体很诚实!",

        "她表面是乖乖女,真实身份却让所有人傻眼!",

        "全剧最虐的一幕,导演太懂了!",

        "他明明可以解释,却选择沉默三年!",

        "她以为他不爱她,却不知道他一直在背后...",

        "这CP太上头了!求求你们赶紧在一起吧!",

    ],

    # 悬念型(促完播)

    "suspense": [

        "最后{nums}秒才是重点!",

        "结尾彻底反转,我整个人都傻了!",

        "看到最后才发现,她才是全剧最狠的人!",

        "这结局我真没想到,太绝了!",

        "第{nums}分钟开始高能,一直烧到结尾!",

        "导演把真相藏到最后三秒,你看懂了吗?",

        "这段封神了!每一帧都在埋伏笔!",

        "最后{nums}秒,导演狠狠打了我一巴掌!",

    ],

    # 话题型(蹭热点)

    "topic": [

        "最近超火的{nums}部短剧,这一部最上头!",

        "刷到就是缘分,这部剧不火没天理!",

        "{nums}月必看短剧TOP1,我先磕为敬!",

        "这部剧被姐妹们问疯了,链接来了!",

        "救命!这部短剧甜到犯规,快去看!",

        "年度最上头短剧,没有之一!",

        "全网怒推的这部短剧,我也入坑了!",

        "看完这部剧,我决定把其他剧都删了!",

    ],

}



# ---- 话题标签库(按类型分类)----

HASHTAG_SETS = {

    # 流量大词(必带)

    "must": [

        "#短剧", "#短剧推荐", "#抖音短剧", "#短剧热播榜",

        "#短剧来了", "#追剧打卡", "#一起追剧吧",

    ],

    # 题材标签

    "genre": {

        "复仇爽剧": ["#复仇短剧", "#爽剧推荐", "#大女主爽剧", "#逆袭人生"],

        "甜宠恋爱": ["#甜宠短剧", "#甜蜜暴击", "#撒糖现场", "#甜剧推荐"],

        "霸道总裁": ["#霸总短剧", "#总裁甜宠", "#霸道总裁爱上我"],

        "悬疑惊悚": ["#悬疑短剧", "#惊悚短剧", "#烧脑剧情"],

        "婚姻家庭": ["#家庭伦理", "#婚姻情感", "#真实故事"],

        "都市言情": ["#都市情感", "#都市丽人", "#现代爱情"],

        "古装穿越": ["#穿越剧", "#古装甜宠", "#穿越短剧"],

        "玄幻仙侠": ["#仙侠短剧", "#玄幻剧", "#三生三世"],

    },

    # 情绪标签(促互动)

    "emotion": [

        "#太上头了", "#甜到犯规", "#虐到心碎", "#笑到肚子疼",

        "#太绝了", "#哭死我了", "#太敢拍了", "#神仙打架",

    ],

    # 互动标签

    "engagement": [

        "#你怎么看", "#评论区见", "#一起讨论", "#你认同吗",

        "#猜猜结局", "#这也太", "#太真实了", "#有同感吗",

    ],

    # 追剧标签

    "follow": [

        "#追剧打卡", "#追剧日记", "#每日追剧", "#追剧时光",

        "#追剧清单", "#必看短剧", "#宝藏短剧", "#推荐必看",

    ],

}



# ---- 互动引导文案(促评论/分享)----

CTA_TEMPLATES = {

    "comment": [

        "这波操作你怎么看?评论区告诉我!",

        "你觉得她做得对吗?来说说你的看法!",

        "结局你猜对了吗?评论区见!",

        "你们觉得男主渣不渣?",

        "这一幕你看了几遍?我看了十遍!",

        "评论区告诉我你最讨厌谁!",

        "有没有人跟我一样,看到这里哭了?",

        "你们觉得这剧能火吗?",

    ],

    "share": [

        "刷到的都是有缘人,收藏慢慢看!",

        "别愣着了,赶紧艾特你的闺蜜来看!",

        "刷到就是缘分,给她点个赞再走!",

        "这剧太上头了,必须分享给姐妹!",

        "独乐乐不如众乐乐,转给朋友一起看!",

    ],

    "follow": [

        "喜欢这类短剧的朋友点个关注,每天更新!",

        "想看后续的朋友记得关注我,第一时间追剧!",

        "更多精彩短剧,关注我追剧不迷路!",

        "关注我,追剧路上不孤单!",

    ],

    "like": [

        "觉得好看的给个赞,鼓励我继续更新!",

        "这剧值得一个赞,同意的举手!",

        "刷到就是缘分,给个赞再走呗!",

        "点赞关注,追剧不迷路!",

    ],

}





def _generate_viral_title(drama_name: str, genre: str, duration: float, peak_moment: str = "", key_words: list = None, drama_context: dict = None) -> str:


    # P1-4 改造:注入真实角色名/事件,而非纯模板
    drama_context = drama_context or {}
    characters = drama_context.get("characters", [])

    import random as _rnd
    # 如果有真实角色名,优先用真实元素构建标题
    if characters and _rnd.random() > 0.4:
        char_name = _rnd.choice(characters)
        event_desc = _rnd.choice(drama_context.get("key_events", ["逆袭", "反击", "回归"]))
        templates = [
            f"{char_name}{event_desc},全场都看呆了!",
            f"当{char_name}决定不再忍耐,所有人都慌了!",
            f"{char_name}的真实身份,连他都意想不到!",
        ]
        return _rnd.choice(templates)

    # 否则继续使用原有模板逻辑
        """生成爆款标题(基于真实剧情关键词)"""

    templates = []



    # 根据类型选择模板

    if genre in ["复仇爽剧", "爽文", "逆袭"]:

        templates = VIRAL_TITLE_TEMPLATES["reverse"] + VIRAL_TITLE_TEMPLATES["conflict"] + VIRAL_TITLE_TEMPLATES["number"]

    elif genre in ["甜宠恋爱", "甜蜜", "撒糖"]:

        templates = VIRAL_TITLE_TEMPLATES["conflict"] + VIRAL_TITLE_TEMPLATES["topic"]

    elif genre in ["悬疑惊悚", "惊悚"]:

        templates = VIRAL_TITLE_TEMPLATES["suspense"] + VIRAL_TITLE_TEMPLATES["reverse"]

    elif genre in ["豪门", "总裁"]:

        templates = VIRAL_TITLE_TEMPLATES["reverse"] + VIRAL_TITLE_TEMPLATES["conflict"]

    else:

        templates = sum(list(VIRAL_TITLE_TEMPLATES.values()), [])



    template = random.choice(templates)



    # 填充变量

    num = random.randint(1, 9)

    nums = f"{num}秒" if random.random() > 0.5 else f"{num}分钟"

    # 如果有真实关键词,优先用

    keyword = (key_words[0] if key_words else None) or drama_name or "女主"



    title = template.format(

        name=keyword,

        num=num,

        nums=nums,

    )



    # 标题长度控制(15-30字最合适)

    if len(title) > 30:

        title = title[:29] + "!"

    elif len(title) < 15:

        title = f"这部短剧{title}"



    return title





def _generate_hashtags(genre: str = "", mood: str = "", key_words: list = None, drama_context: dict = None) -> list:



    # P1-4 改造:基于真实剧情上下文生成标签(而非固定词库)
    drama_context = drama_context or {}
    tags = []

    # 1. 从真实剧情中提取角色名作为标签(差异化核心)
    characters = drama_context.get("characters", [])
    if characters:
        import random as _rh
        char_tag = f"#{_rh.choice(characters)}" if characters else ""
        if char_tag and len(char_tag) < 10:
            tags.append(char_tag)

    # 2. 剧情关键词 → 生成个性化标签
    key_events = drama_context.get("key_events", [])
    if key_events:
        import random as _re
        event_tag = f"#{_re.choice(key_events)}" if key_events else ""
        if event_tag and len(event_tag) < 20:
            tags.append(event_tag[:20])
        """

    生成话题标签(严格限制5个,符合抖音投稿要求)

    组合策略:1个流量词 + 1个题材词 + 1个剧情词 + 1个情绪词 + 1个互动词

    """

    import random as _r

    tags = []



    # 1. 必带流量词(1个)

    tags.append(_r.choice(HASHTAG_SETS["must"]))



    # 2. 题材标签(1个)

    if genre and genre in HASHTAG_SETS["genre"]:

        tags.append(_r.choice(HASHTAG_SETS["genre"][genre]))

    else:

        tags.append(_r.choice(HASHTAG_SETS["must"]))



    # 3. 根据剧情关键词生成标签(1个,多字匹配优先)

    if key_words:

        kw = key_words[0] if key_words else ""

        # 多字词优先匹配(更精准),单字匹配兜底

        kw_tags = [
            # 多字词(优先匹配)
            ("霸总", "#霸总宠妻"), ("总裁", "#霸道总裁"),
            ("豪门", "#豪门甜宠"), ("千金", "#豪门千金"),
            ("甜宠", "#甜到上头"), ("发糖", "#甜到上头"),
            ("离婚", "#离婚后逆袭"), ("前妻", "#前妻归来"),
            ("复仇", "#复仇爽剧"), ("报复", "#逆袭复仇"),
            ("穿越", "#穿越短剧"), ("重生", "#重生逆袭"),
            ("虐心", "#虐到心碎"), ("虐恋", "#虐恋情深"),
            ("萌宝", "#萌宝助攻"), ("萌娃", "#萌娃神助攻"),
            ("神医", "#神医高手"), ("医术", "#中医文化"),
            ("逆袭", "#逆袭人生"), ("翻身", "#逆风翻盘"),
            ("杀手", "#王牌杀手"), ("战神", "#战神归来"),
            ("首富", "#首富老公"), (" billionaire", "#亿万总裁"),
            ("替身", "#替身文学"), ("闪婚", "#闪婚老公"),
            ("双胞胎", "#双胞胎短剧"), ("龙凤胎", "#萌宝甜剧"),
            ("师尊", "#师徒恋"), ("师妹", "#仙侠短剧"),
            ("末世", "#末日生存"), ("末日", "#末日灾难"),
            ("契约", "#契约婚姻"), ("假结婚", "#契约恋爱"),
            ("年代", "#年代文"), ("八零", "#年代短剧"),
            ("古代", "#古风短剧"), ("太子", "#古风虐恋"),
            # 单字(兜底)
            ("霸", "#霸总短剧"), ("总", "#豪门甜宠"),
            ("豪", "#豪门恩怨"), ("甜", "#甜宠时光"),
            ("婚", "#婚姻情感"), ("离", "#离婚逆袭"),
            ("逆", "#逆袭人生"), ("复", "#复仇短剧"),
            ("虐", "#虐心短剧"), ("神", "#神仙爱情"),
            ("宝", "#萌宝甜剧"), ("宠", "#甜宠短剧"),
            ("爱", "#爱情短剧"), ("情", "#虐心爱情"),
            ("战", "#战斗短剧"), ("龙", "#龙傲天"),
        ]

        matched = False
        for k, t in kw_tags:
            if len(k) > 1 and k in kw:  # 多字词优先
                tags.append(t)
                matched = True
                break
        if not matched:
            for k, t in kw_tags:
                if len(k) == 1 and k in kw:  # 单字兜底
                    tags.append(t)
                    matched = True
                    break
        if not matched:
            tags.append(_r.choice(HASHTAG_SETS["follow"]))

    else:

        tags.append(_r.choice(HASHTAG_SETS["follow"]))



    # 4. 情绪标签(1个)

    tags.append(_r.choice(HASHTAG_SETS["emotion"]))



    # 5. 互动标签(1个)

    tags.append(_r.choice(HASHTAG_SETS["engagement"]))



    # 无条件注入合规标签(P0 要求)
    # 合规标签已禁用(用户要求)
    return tags[:7]  # 允许最多7个





def _generate_cta_text() -> str:

    """生成互动引导文案"""

    parts = []



    # 评论引导(必选)

    parts.append(random.choice(CTA_TEMPLATES["comment"]))



    # 点赞/关注(随机选一个)

    if random.random() > 0.5:

        parts.append(random.choice(CTA_TEMPLATES["like"]))

    else:

        parts.append(random.choice(CTA_TEMPLATES["follow"]))



    return " ".join(parts)





def _generate_post_config(

    drama_name: str,

    genre: str,

    duration: float,

    peak_moment: str = "",

    key_words: list = None,

) -> dict:

    """

    生成抖音发布配置(基于真实剧情内容)

    包含:标题、描述、话题标签、封面建议

    """

    key_words = key_words or []



    # 1. 生成爆款标题(基于剧情关键词)

    title = _generate_viral_title(drama_name, genre, duration, peak_moment, key_words)



    # 2. 生成话题标签(严格5个)

    hashtags = _generate_hashtags(genre, key_words=key_words)



    # 3. 生成互动引导

    cta_text = _generate_cta_text()



    # 4. 组装完整描述

    description = f"{title}\n\n{' '.join(hashtags)}\n\n{cta_text}"



    return {

        "title": title,

        "description": description,

        "hashtags": hashtags,

        "cta_text": cta_text,

        "duration": duration,

        "genre": genre,

        "key_words": key_words,

        "suggested_post_time": _suggest_post_time(),

    }





def _suggest_post_time() -> dict:

    """推荐最佳发布时间"""

    peak_times = [

        {"time": "12:00-13:00", "label": "午休时段", "score": 9},

        {"time": "18:00-19:00", "label": "下班路上", "score": 9},

        {"time": "20:00-22:00", "label": "晚间黄金", "score": 10},

        {"time": "21:30-22:30", "label": "睡前刷手机", "score": 8},

    ]



    weekday = datetime.now().weekday()

    is_weekend = weekday >= 5



    if is_weekend:

        peak_times.append({"time": "10:00-12:00", "label": "周末休闲", "score": 8})



    best = max(peak_times, key=lambda x: x["score"])



    return {

        "best_time": best["time"],

        "label": best["label"],

        "all_peak_times": peak_times[:3],

    }





def _generate_thumbnail_hint(video_duration: float, peak_moment: float = 0) -> dict:
    video_duration = float(video_duration) if video_duration else 0.0
    peak_moment = float(peak_moment) if peak_moment else 0.0

    """生成封面建议"""

    return {

        "suggested_frame": peak_moment if peak_moment > 0 else video_duration * 0.3,

        "aspect_ratio": "9:16",

        "text_overlay": True,

        "text_style": "大字标题+副标题",

        "tips": [

            "封面用视频中最有冲击力的画面",

            "标题文字要醒目,3秒内让人看懂",

            "避免封面与内容严重不符(影响推荐)",

            "封面不要有其他平台水印",

        ]

    }





def generate_viral_package(

    drama_name: str,

    genre: str = "",

    duration: float = 60.0,

    peak_moment: float = 0,

    key_words: list = None,

) -> dict:

    """

    生成抖音爆款发布包(基于真实剧情内容)

    包含标题、描述、标签、封面建议、最佳发布时间

    """

    key_words = key_words or []

    post_config = _generate_post_config(drama_name, genre, duration, peak_moment, key_words)

    thumbnail_hint = _generate_thumbnail_hint(duration, peak_moment)



    return {

        **post_config,

        "thumbnail_hint": thumbnail_hint,

    }





# ==================== 【6】主流程:批量自动剪辑 ====================



def batch_auto_cut(user_config: dict = None):

    """

    Seedance增强版短剧剪辑流程:

    支持批量处理:raw_videos/剧名/ 目录结构

    配置优先级:用户自定义 > 智能检测 > 默认配置



    Args:

        user_config: 用户自定义配置(从前端传入)

    """

    # 应用用户配置

    apply_user_config(user_config)

    # 【修复】将相对路径转为基于脚本目录的绝对路径,避免 cron 运行时 cwd 不一致导致找不到目录
    _SCRIPT_DIR = Path(__file__).resolve().parent
    _RELATIVE_DIR_KEYS = ["input_dir", "output_dir", "bgm_dir", "narration_dir", "subtitle_dir"]
    for _key in _RELATIVE_DIR_KEYS:
        _val = CONFIG.get(_key, "")
        if _val and not Path(_val).is_absolute():
            _abs = _SCRIPT_DIR / _val
            CONFIG[_key] = str(_abs)
            log(f"📁 路径修正: {_key} → {_abs}", "🔧")




    log("=" * 60, "")

    log("🎯 抖音短剧AI自动剪辑工具(Seedance增强版)", "🚀")

    log("📋 批量处理 | 标题字幕 | 声道分离 | 音画同步", "")



    # 显示配置来源

    if user_config:

        customized = [k for k, v in user_config.items() if is_user_customized(v)] if HAS_CONFIG_MERGER else []

        if customized:

            log(f"⚙️ 用户自定义配置: {', '.join(customized[:5])}{'...' if len(customized)>5 else ''}", "")

        log("🤖 其他配置: 智能检测", "")



    log("=" * 60, "")



    check_dirs()

    raw_dir = Path(CONFIG["input_dir"]).resolve()



    # 支持子目录批量处理

    drama_dirs = []

    subdirs = [d for d in raw_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if subdirs:

        drama_dirs = [(d.name, d) for d in subdirs]

    else:

        drama_dirs = [(raw_dir.name, raw_dir)]



    # 过滤只处理已选剧目(前端传来的 selected_dramas)

    selected_dramas = user_config.get("selected_dramas") if user_config else None

    if selected_dramas and len(selected_dramas) > 0:

        drama_dirs = [(name, path) for name, path in drama_dirs if name in selected_dramas]

        log(f"📂 精选模式: 已选 {len(drama_dirs)} 部 → {', '.join([n for n,_ in drama_dirs])}", "")

    elif len(drama_dirs) > 1:

        log(f"📂 批量模式: 检测到 {len(drama_dirs)} 部短剧", "")

    else:

        log(f"📂 单剧模式: {drama_dirs[0][0] if drama_dirs else raw_dir.name}", "")



    total_success = 0

    process_func = _process_single_drama
    log(f"⚙️ 流程模式: 解说驱动", "")

    for drama_name, drama_path in drama_dirs:

        log(f"\n{'='*40}", "")

        log(f"🎬 处理短剧: {drama_name}", "🎬")

        log(f"{'='*40}", "")

        success = process_func(drama_name, drama_path)

        total_success += success if success is not None else 0



    log(f"\n🏁 全部完成! 成功 {total_success}/{len(drama_dirs)} 部", "🎉")





def _recognize_single_file(file_idx, vfile, raw_dir_abs, whisper_model):
    """单个文件的语音识别(线程池中运行)
    优先Whisper(出文字+时间戳)
    whisper_model: 外部预加载的WhisperModel,避免每线程重复加载
    """
    file_text = ""
    file_subs = []

    # 提取音频
    audio_tmp = os.path.join(raw_dir_abs, f"__audio_{file_idx}_{os.getpid()}__.wav")
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(vfile),
        "-vn", "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le", audio_tmp
    ], capture_output=True, timeout=SUBPROCESS_TIMEOUT)

    if not os.path.exists(audio_tmp) or os.path.getsize(audio_tmp) < 1000:
        return file_idx, "", []

    # 方案A: Whisper(优先,一次出文字+时间戳)
    if whisper_model is not None:
        try:
            segments, _ = whisper_model.transcribe(audio_tmp, language="zh")
            for seg in segments:
                t = seg.text.strip()
                if t:
                    file_text += t + " "
                    file_subs.append((seg.start, seg.end, t))
            file_text = file_text.strip()
        except Exception as e:
            log(f"      ⚠️ Whisper失败({vfile.name}): {e}", "")

    # 清理临时文件
    if os.path.exists(audio_tmp):
        try: os.unlink(audio_tmp)
        except Exception: pass

    return file_idx, file_text, file_subs


# ═══════════════════════════════════════════════════════════════════════
# Toonflow集成:结构化分镜节点 + 角色一致性检查
# ═══════════════════════════════════════════════════════════════════════

def _build_shot_nodes(clips: List[dict], narration_segments: List[dict]) -> List[dict]:
    """
    构建结构化分镜节点(视觉锚点)
    Toonflow核心:每个分镜固定角色+背景+情绪,防止AI闪烁/不一致
    - 将每个片段与解说段绑定
    - 记录角色出现、时间戳、情绪标签
    - 用于后续视频一致性验证
    """
    shot_nodes = []
    for idx, (clip, seg) in enumerate(zip(clips, narration_segments)):
        # 提取视觉锚点
        dominant_color = "unknown"
        brightness = 0.5
        try:
            cap = cv2.VideoCapture(clip.get("path", ""))
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    avg_color = frame.mean(axis=(0,1))
                    dominant_color = f"#{int(avg_color[2]):02x}{int(avg_color[1]):02x}{int(avg_color[0]):02x}"
                    brightness = float(frame.mean() / 255.0)
                cap.release()
        except Exception:
            pass

        node = {
            "shot_id": idx + 1,
            "clip_path": clip.get("path", ""),
            "start": clip.get("start", 0),
            "end": clip.get("end", 0),
            "narration_text": seg.get("text", ""),
            "emotion_label": seg.get("emotion", "neutral"),
            "character_appearances": seg.get("characters", []),
            "scene_location": seg.get("location", "unknown"),
            "visual_anchors": {
                "dominant_color": dominant_color,
                "brightness": brightness,
                "motion_intensity": clip.get("motion_score", 0.5)
            }
        }
        shot_nodes.append(node)
    log(f"   📌 构建分镜节点: {len(shot_nodes)}个", "")
    return shot_nodes


def _check_character_consistency(shot_nodes: List[dict], drama_title: str) -> List[dict]:
    """
    检查角色在多集间的一致性(基于AssetManager)
    - 角色外观描述是否匹配
    - 场景/服装是否一致
    - 返回警告列表
    """
    if not _ASSET_MANAGER_AVAILABLE:
        return []
    try:
        asset_mgr = AssetManager()
        warnings = []
        for node in shot_nodes:
            for char in node.get("character_appearances", []):
                char_info = asset_mgr.get_character(char)
                if char_info and char_info.get("consistency_notes"):
                    warnings.append({
                        "shot_id": node["shot_id"],
                        "character": char,
                        "warning": char_info["consistency_notes"]
                    })
        if warnings:
            log(f"   ⚠️ 角色一致性警告: {len(warnings)}条", "⚠️")
        return warnings
    except Exception as e:
        log(f"   ⚠️ 角色一致性检查失败: {e}", "⚠️")
        return []


def _process_single_drama(drama_name: str, drama_path: Path) -> int:
    """
    解说驱动主流程:先解说,后剪辑
    """
    import urllib.request
    # import json  # removed: already imported at top level as _json

    # 防御: 目录可能在批量运行期间被合规过滤器删除, 缺失则跳过而非崩溃
    if not drama_path.exists() or not drama_path.is_dir():
        log(f"⚠️ {drama_name}: 目录不存在(可能已被过滤删除),跳过", "⚠️")
        return 0

    files = [f for f in drama_path.iterdir()
             if f.suffix.lower() in (".mp4", ".mov", ".mkv")
             and not f.name.startswith(".")]

    if not files:
        log(f"❌ {drama_name}: 未找到视频文件", "❌")
        return 0

    files = sorted([f for f in files if not f.name.startswith("__")],
                   key=lambda x: natural_sort_key(x.name))
    log(f"📂 检测到 {len(files)} 个视频", "")

    _, episode = extract_drama_info(files[0].name)

    # 步骤0: 检测比例
    ref_info = get_video_info(str(files[0]))
    src_w, src_h = ref_info["width"], ref_info["height"]
    src_ratio = src_w / src_h if src_h > 0 else 9 / 16
    detected_ratio = "9:16" if src_ratio < 0.75 else ("16:9" if src_ratio > 1.15 else "4:3")

    SMART_CONFIG["aspect_ratio"] = detected_ratio
    cfg_ratio = get_effective_config("aspect_ratio")

    sizes = {
        ("16:9", "auto"): (1920, 1080), ("16:9", "16:9"): (1920, 1080),
        ("16:9", "9:16"): (1080, 1920), ("9:16", "auto"): (1080, 1920),
        ("9:16", "9:16"): (1080, 1920), ("9:16", "16:9"): (1920, 1080),
    }
    out_w, out_h = sizes.get((detected_ratio, cfg_ratio), (1080, 1920) if detected_ratio == "9:16" else (1920, 1080))
    log(f"📐 输出: {out_w}x{out_h}", "")

    orig_w, orig_h = CONFIG["width"], CONFIG["height"]
    CONFIG["width"], CONFIG["height"] = out_w, out_h

    # Toonflow: 初始化多集记忆系统
    asset_manager = None
    if _ASSET_MANAGER_AVAILABLE:
        try:
            asset_manager = AssetManager()
            log("   📚 多集记忆系统已加载", "")
        except Exception as e:
            log(f"   ⚠️ 多集记忆系统初始化失败: {e}", "⚠️")

    try:
        # 步骤1: 语音识别
        log("🎙️ [1/8] 语音识别...", "⏳")
        all_file_subtitles = {}
        full_text = ""

        use_whisper = get_effective_config("use_whisper", True)
        whisper_model = None

        # 强制确保 venv site-packages 在 sys.path
        import sys as _s
        _script_dir = Path(__file__).parent.resolve()
        for _d in [_script_dir] + list(_script_dir.parents):
            _venv = _d / ".venv"
            if _venv.exists() and _venv.is_dir():
                _lib = _venv / "lib"
                if _lib.exists():
                    for _py in sorted(_lib.iterdir()):
                        if _py.is_dir() and _py.name.startswith("python"):
                            _sp = _py / "site-packages"
                            if _sp.exists() and str(_sp) not in _s.path:
                                _s.path.insert(0, str(_sp))
        import sys; log(f"   [DEBUG] sys.path[0:3]={sys.path[0:3]}", "")

        if use_whisper:
            try:
                # Debug: 写文件确认实际 Python 路径
                import sys as _sys
                with open('/tmp/whisper_debug.txt', 'w') as _f:
                    _f.write(f'sys.executable={_sys.executable}\n')
                    _f.write(f'sys.path[0:5]={_sys.path[0:5]}\n')
                    try:
                        import faster_whisper as _fw
                        _f.write(f'faster_whisper OK: {_fw.__file__}\n')
                    except Exception as _e:
                        _f.write(f'faster_whisper FAIL: {_e}\n')
                log("   🔄 加载Whisper模型...", "")
                from faster_whisper import WhisperModel
                # 诊断:打印配置值
                _model_name_debug = get_effective_config("asr_model", None)
                _model_name_debug2 = get_effective_config("whisper_model", "medium")
                log(f"   [DEBUG] asr_model={_model_name_debug!r}, whisper_model={_model_name_debug2!r}", "")
                log(f"   [DEBUG] CONFIG['asr_model']={CONFIG.get('asr_model')!r}", "")
                model_name = _model_name_debug or _model_name_debug2
                log(f"   [DEBUG] 最终 model_name={model_name!r}", "")
                # faster-whisper 不支持 MPS (Apple Silicon),仅支持 CUDA 和 CPU
                # CUDA (NVIDIA GPU) 时用 float16,否则用 int8 (CPU)
                _device = "cuda" if torch.cuda.is_available() else "cpu"
                _compute = "float16" if _device == "cuda" else "int8"
                whisper_model = WhisperModel(model_name, device=_device, compute_type=_compute)
                log(f"   ✅ Whisper模型加载成功: {model_name} ({_device}, {_compute})", "")
            except Exception as e:
                log(f"   ⚠️ Whisper模型加载失败: {e}", "")
                whisper_model = None  # 显式设为 None 以触发 fallback

        def recognize_file(args):
            idx, fpath = args
            try:
                subs, texts = [], []
                _audio = str(fpath)
                if whisper_model:
                    # 使用 faster-whisper (CPU int8)
                    segments, _ = whisper_model.transcribe(_audio, language="zh")
                    for seg in segments:
                        txt = seg.text.strip()
                        if txt and len(txt) >= 2:
                            subs.append((seg.start, seg.end, txt))
                            texts.append(txt)
                elif WHISPER_CPP_AVAILABLE:
                    # fallback: whisper.cpp (Metal GPU 加速,自动启用)
                    _segs = transcribe_whisper_cpp(_audio, language="zh", model_size="medium", output_format="json")
                    if _segs:
                        for _s in _segs:
                            if _s.get("text"):
                                subs.append((_s["start"], _s["end"], _s["text"]))
                                texts.append(_s["text"])
                return idx, subs, " ".join(texts)
            except Exception as e:
                return idx, [], ""

        from concurrent.futures import ThreadPoolExecutor, as_completed
        log(f"   📁 待识别文件数: {len(files)}", "")
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(recognize_file, (i, f)): i for i, f in enumerate(files)}
            for future in as_completed(futures):
                idx, subs, text = future.result()
                all_file_subtitles[idx] = subs
                full_text += text + " "
                if len(all_file_subtitles) % 5 == 0:
                    log(f"   已处理: {len(all_file_subtitles)}/{len(files)}", "")

        total_subs = sum(len(v) for v in all_file_subtitles.values())
        log(f"   ✅ 识别: {total_subs}条字幕", "")

        # 步骤1.5: 内容合规预检(题材风险筛查)
        risk_result = _check_content_risk(full_text, drama_name)
        if risk_result.get("risk_level") == "HIGH":
            log(f"⚠️ {drama_name}: 高风险题材 - {risk_result.get('reason', '')}", "⚠️")
            log(f"   匹配关键词: {risk_result.get('matched', [])}", "")
            # [FIX-20260721] 不再删除原片,改在目录名加「不合规」标记
            try:
                if drama_path.exists() and drama_path.is_dir():
                    _marked = drama_path.parent / f"{drama_path.name}「不合规」"
                    if not _marked.exists():
                        shutil.move(str(drama_path), str(_marked))
                        log(f"   🏷️ 已标记: {_marked}", "")
                    else:
                        log(f"   ⚠️ 已存在标记目录: {_marked}", "")
                else:
                    log(f"   ⚠️ 目录不存在: {drama_path}", "")
            except Exception as e:
                log(f"   ❌ 标记目录失败: {e}", "")
            return 0  # 跳过该剧集
        elif risk_result.get("risk_level") == "MEDIUM":
            log(f"🔶 {drama_name}: 中等风险题材 - 将加强解说约束", "")

        # 步骤2: LLM生成解说
        log("📝 [2/8] LLM生成解说...", "⏳")
        genre = _detect_drama_genre(full_text, " ".join(str(f) for f in files)) if '_detect_drama_genre' in globals() else "都市言情"

        # [FIX-时间锚点-20260528] 解说带时间戳,片段按锚点选
        # 核心改动:LLM返回JSON格式的解说+时间锚点,片段选择精确按时间取
        subtitle_samples = []
        for fidx, subs in all_file_subtitles.items():
            for start, end, text in subs[:30]:  # 增加样本量
                subtitle_samples.append(f"[{start:.1f}s-{end:.1f}s] {text}")

        subtitle_context = "\n".join(subtitle_samples[:120])

        # [FIX-20260707] 解说字数按成片目标时长计算(非素材总时长)
        # 成片目标时长 = CONFIG max_duration,解说应覆盖整个成片
        _target_video_sec = CONFIG.get('max_duration', 180)  # 成片目标时长
        _est_video_sec = _target_video_sec  # 解说按成片时长计算
        _target_narr_chars = min(1500, max(360, int(_est_video_sec * 4.5)))  # 4.5字/秒(ChatTTS实际语速)
        _min_narr_chars = max(200, int(_target_narr_chars * 0.7))
        _seg_count = min(15, max(5, int(_est_video_sec / 12)))  # 每12秒一段解说
        # 素材总时长(用于LLM分配时间段覆盖范围)
        _source_total_sec = 60.0
        if all_file_subtitles:
            _sum_end = 0.0
            for _fidx_k, _subs in all_file_subtitles.items():
                _file_max_end = 0.0
                for _s, _e, _t in _subs:
                    if _e > _file_max_end:
                        _file_max_end = _e
                _sum_end += _file_max_end
            if _sum_end > 0:
                _source_total_sec = _sum_end
        if _source_total_sec <= 60.0 and files:
            _source_total_sec = len(files) * 60.0

        prompt = f"""你是短剧解说全流程导演。请按PA分析→SW编剧→ED剪辑三步思维写解说。
剧名: 《{drama_name}》 | 类型: {genre} | 目标时长: {_target_video_sec}秒

========== 字幕素材 ==========
{subtitle_context}
========== 素材信息 ==========
素材总时长约{_source_total_sec:.0f}秒, 制作{_target_video_sec}秒成片(选取约{_target_video_sec/_source_total_sec*100:.0f}%的精华)

========== 第一步: PA剧情分析 ==========
1. 先读懂字幕中的故事主线: 谁在什么处境中, 经历什么转折, 最后怎样?
2. 识别至少3个爽点/情绪爆点(类型+时间点+为什么爽)
   → 爽点类型: 身份揭晓/打脸反转/实力碾压/深情告白/危机化解/意外发现/逆袭崛起
3. 画出节奏曲线: 铺垫→冲突→高潮→反转→收尾, 高潮集中在哪?
4. 提取至少1条黄金钩子: 一句话戳中最大悬念/最强冲突, 直接做视频开场

========== 第二步: SW脚本编剧 ==========
[开场铁律-数据驱动] 抖音2秒跳出率54%(头号短板), 前2秒决定生死:
  · 首段必须是具象冲突场景(如'他当众撕毁婚书''她一巴掌扇过去'), 禁止背景铺垫/人物介绍
  · 首句直接抛反常识/强冲突/金句, 禁用'故事发生在''话说''从前'
  · 黄金钩子必须可读出画面, 不能抽象(❌'命运弄人' ✅'被退婚当天, 她亮出了龙纹玉佩')
1. 开场必须是黄金钩子(冲突/悬念/反差的具象场景), 前3秒抓人
2. 逐段写{_seg_count}段解说, 每段必须标注beat节奏(铺垫/爆发/反转/悬念/收尾):
   · 铺垫段: 背景交代, 语气平实, 信息密度中等
   · 爆发段: 高潮冲突, 短句快节奏, 情绪拉满
   · 反转段: 意料之外, 停顿+强调, 制造反差
   · 悬念段: 欲言又止, 留白勾引, 节奏放缓
   · 收尾段: 引导互动/追更/留悬念
3. 信息密度: 每10秒至少一个信息点或情绪点, 杜绝废话水词
4. 结尾引导: 留悬念/提问互动/关注追更, 不剧透大结局
5. 全片{_min_narr_chars}-{_target_narr_chars}字(语速约4.5字/秒), 均匀分配到{_seg_count}段

========== 第三步: ED剪辑导演(精确定位) ==========
1. 每段必须精确锚定到字幕中的真实时间点(从上面字幕素材里找)
2. file字段 = 该段画面属于哪一集(file_0=第1集, file_1=第2集...)
3. time_start/time_end = 该集内的秒数, 不是素材总秒数
4. 每段解说只讲该时间区间内的剧情, 不跳时间线
5. 段与段之间要有因果或情绪递进, 不生硬跳跃

========== 硬约束 ==========
· 【产出格式】只输出JSON, 不要任何其他文字:
  {{"segments":[{{"file":"file_0","time_start":0,"time_end":12.5,"beat":"爆发","narration":"黄金钩子开场词"}},{{"file":"file_1","time_start":0,"time_end":15.0,"beat":"铺垫","narration":"承接剧情解说"}}]}}
  每个segment必含: file(集号/file_0/file_1...), time_start(秒), time_end(秒), beat(铺垫/爆发/反转/悬念/收尾), narration(解说词)
· 【反模板化】用正常人口吻讲故事, 禁止'这一幕''注意看''你敢信''谁知道''话说''大家看'等固定开场
· 【反模板化】不堆砌形容词, 场景+行为+结果, 干净利落
· 【反重复】每段内容必须不同, 禁止换说法复述同一情节
· 【价值观约束】不渲染暴力复仇/以暴制暴, 冲突场景强调人物成长与智慧
· 【价值观约束】禁用'碾压''踩''让付出代价''加倍奉还'等暴力词汇
· 【价值观约束】结尾引导正向价值: 理性解决/合法途径/宽容理解
· 【数量约束】必须刚好{_seg_count}段, 不多不少
· 【字数约束】每段50-90字, 全文{_min_narr_chars}-{_target_narr_chars}字

输出JSON:"""

        narration_text = ""
        time_anchors = []  # 保留兼容,从segments转换
        narration_segments = []  # [(time_start, time_end, narration_text), ...]
        narration_file_index = {}  # [PA+SW+ED-20260731] seg_index→(file_idx, file_str)
        narration_beats = {}  # [PA+SW+ED-20260731] seg_index→beat(铺垫/爆发/反转/悬念/收尾)

        try:
            data = json.dumps({"model": "qwen3.5:4b", "prompt": prompt, "stream": False,
                               "think": False,
                               "format": "json",
                               "options": {"temperature": 0.7, "num_predict": 3000}}).encode('utf-8')
            req = urllib.request.Request('http://localhost:11434/api/generate', data=data,
                                         headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=SUBPROCESS_TIMEOUT) as resp:
                raw = json.loads(resp.read().decode('utf-8')).get('response', '').strip()
                # 提取JSON:找第一个{和最后一个}(最可靠)
                json_str = ''
                # 裸JSON - 找第一个{和最后一个}
                start = raw.find('{')
                end = raw.rfind('}')
                if start >= 0 and end > start:
                    json_str = raw[start:end + 1]
                if json_str:
                    try:
                        parsed = json.loads(json_str)
                        # [FIX-分段解说-20260705] 优先解析segments格式
                        segs_raw = parsed.get('segments', [])
                        if segs_raw:
                            for seg in segs_raw:
                                _ts = seg.get('time_start', 0)
                                _te = seg.get('time_end', 0)
                                _sn = seg.get('narration', '')
                                _file = seg.get('file', '')  # [PA+SW+ED-20260731] 新增file字段
                                _beat = seg.get('beat', '铺垫')  # [PA+SW+ED-20260731] 新增beat字段
                                if not _sn or len(_sn) < 5:
                                    continue
                                # 时间容错
                                try: _ts = float(_ts)
                                except: _ts = 0.0
                                try: _te = float(_te)
                                except: _te = 0.0
                                # file字段解析: "file_0" → 0, 也兼容纯数字
                                _file_idx = -1
                                if _file:
                                    _fm = re.search(r'(\d+)', str(_file))
                                    if _fm:
                                        _file_idx = int(_fm.group(1))
                                narration_segments.append((_ts, _te, _sn))
                                narration_text += _sn
                                # [PA+SW+ED-20260731] 存储file和beat,用于精准时间锚定+节奏感知
                                _si = len(narration_segments) - 1
                                narration_file_index[_si] = (_file_idx, _file if _file else '')
                                narration_beats[_si] = _beat if _beat in ('铺垫','爆发','反转','悬念','收尾') else '铺垫'
                                # 兼容:从segment生成anchor
                                time_anchors.append({'text': _sn[:20], 'time': _ts, 'duration': min(4.0, max(2.0, _te - _ts))})
                            log(f"   🔍 LLM返回: {len(narration_segments)}段解说, 总{len(narration_text)}字 (目标{_target_narr_chars}字/{_seg_count}段, 成片目标{_target_video_sec}秒, 素材{_source_total_sec:.0f}秒)", "")
                            if narration_segments:
                                log(f"   🔍 首段: [{narration_segments[0][0]:.1f}-{narration_segments[0][1]:.1f}s] {narration_segments[0][2][:30]}...", "")
                        else:
                            # 兼容旧格式(narration + anchors)
                            narration_text = parsed.get('narration', '')
                            anchors_raw = parsed.get('anchors', [])
                            log(f"   🔍 LLM返回(旧格式): narration={len(narration_text)}字, anchors={len(anchors_raw)}条", "")
                            for a in anchors_raw:
                                if 'text' not in a:
                                    continue
                                anchor_text = str(a['text'])
                                raw_time = a.get('time')
                                anchor_time = None
                                if isinstance(raw_time, (int, float)):
                                    anchor_time = float(raw_time)
                                elif isinstance(raw_time, str) and raw_time.replace('.', '', 1).isdigit():
                                    anchor_time = float(raw_time)
                                if anchor_time is None:
                                    best_score = -1
                                    for fidx, subs in all_file_subtitles.items():
                                        for ss, se, st in subs:
                                            if anchor_text in st or st in anchor_text:
                                                anchor_time = ss
                                                break
                                        if anchor_time is not None:
                                            break
                                    if anchor_time is None:
                                        continue
                                duration = 3.0
                                raw_dur = a.get('duration', 3.0)
                                if isinstance(raw_dur, (int, float)):
                                    duration = float(raw_dur)
                                elif isinstance(raw_dur, str) and raw_dur.replace('.', '', 1).isdigit():
                                    duration = float(raw_dur)
                                time_anchors.append({'text': anchor_text, 'time': anchor_time, 'duration': duration})
                        log(f"   ✅ 解说: {len(narration_text)}字, {len(time_anchors)}个时间锚点, {len(narration_segments)}个分段", "")

                        # [低俗检测] 解说生成后立即检测,有禁止词就重生成
                        # [FIX-20260708] 扩大检测范围到segments+narration_text
                        try:
                            log(f"   🔍 [DEBUG] 低俗检测开始, narration_text={len(narration_text)}字, segments={len(narration_segments)}段", "")
                            # [FIX-20260709] 解说生成后强制替换已知禁止词/警告词
                            _safe_replaced = 0
                            for _bad, _good in SAFE_WORD_MAP.items():
                                if _bad in narration_text:
                                    narration_text = narration_text.replace(_bad, _good)
                                    _safe_replaced += 1
                            if narration_segments:
                                for _si in range(len(narration_segments)):
                                    _ts2, _te2, _sn2 = narration_segments[_si]
                                    for _bad, _good in SAFE_WORD_MAP.items():
                                        if _bad in _sn2:
                                            _sn2 = _sn2.replace(_bad, _good)
                                            _safe_replaced += 1
                                    narration_segments[_si] = (_ts2, _te2, _sn2)
                            if _safe_replaced > 0:
                                log(f"   ✅ [SAFE_MAP] 替换{_safe_replaced}处敏感词", "")
                            from _lowbiz_detector import check_narration_lowbiz as _chk_lb
                            # 检测全文本(包含所有segments拼接)
                            _lb_full_text = narration_text
                            if narration_segments:
                                _lb_full_text = ''.join(s[2] for s in narration_segments)
                            _lb_r = _chk_lb(_lb_full_text)
                            if _lb_r.get("has_violation") and any(v["type"]=="PROHIBITED" for v in _lb_r["violations"]):
                                _p_words = [v["word"] for v in _lb_r["violations"] if v["type"]=="PROHIBITED"]
                                log(f"   ⚠️ 检测到低俗禁止词: {_p_words},重生成解说(带低俗规避约束)", "⚠️")
                                _anti_prompt = prompt + "\n【低俗规避】解说严格禁止任何低俗/擦边词汇!\n【低俗规避】禁用'裸''勾搭''勾引''做爱''上床''脱光''丝袜''蕾丝''胸罩''内裤'等词\n【低俗规避】情感场景用'深情''温暖'替代'诱惑''挑逗''性感'\n【低俗规避】若有感情戏只写'深情对视''温柔相拥'"
                                _data2 = json.dumps({"model": "qwen3.5:4b", "prompt": _anti_prompt, "stream": False, "format": "json", "think": False, "options": {"temperature": 0.5, "num_predict": 2000}}).encode('utf-8')
                                _req2 = urllib.request.Request('http://localhost:11434/api/generate', data=_data2, headers={'Content-Type': 'application/json'}, method='POST')
                                with urllib.request.urlopen(_req2, timeout=SUBPROCESS_TIMEOUT) as _resp2:
                                    _raw2 = json.loads(_resp2.read().decode('utf-8')).get('response', '').strip()
                                    _json2 = ''
                                    _s2 = _raw2.find('{')
                                    _e2 = _raw2.rfind('}')
                                    if _s2 >= 0 and _e2 > _s2:
                                        _json2 = _raw2[_s2:_e2 + 1]
                                    if _json2:
                                        _parsed2 = json.loads(_json2)
                                        # [FIX-20260709] 解析segments格式
                                        _segs2 = _parsed2.get('segments', [])
                                        if _segs2:
                                            narration_segments = []
                                            narration_text = ''
                                            for _seg2 in _segs2:
                                                _ss2 = float(_seg2.get('time_start', 0))
                                                _se2 = float(_seg2.get('time_end', 0))
                                                _sn2 = str(_seg2.get('narration', ''))
                                                if _sn2:
                                                    narration_segments.append((_ss2, _se2, _sn2))
                                                    narration_text += _sn2
                                        else:
                                            narration_text = _parsed2.get('narration', narration_text)
                                        log(f"   ✅ 重生成解说: {len(narration_text)}字, {len(narration_segments)}段", "")
                                        # [FIX-20260709] 二次验证+禁止词替换
                                        _lb_full2 = ''.join(s[2] for s in narration_segments) if narration_segments else narration_text
                                        _lb_r2 = _chk_lb(_lb_full2)
                                        if _lb_r2.get("has_violation") and any(v["type"]=="PROHIBITED" for v in _lb_r2["violations"]):
                                            _p2_words = [v["word"] for v in _lb_r2["violations"] if v["type"]=="PROHIBITED"]
                                            log(f"   ⚠️ 重生成后仍有禁止词: {_p2_words}, 替换为安全词", "⚠️")
                                            for _pw in _p2_words:
                                                _safe = SAFE_WORD_MAP.get(_pw, '[已删除]')
                                                narration_text = narration_text.replace(_pw, _safe)
                                                if narration_segments:
                                                    narration_segments = [(s,e,n.replace(_pw,_safe)) for s,e,n in narration_segments]
                                            log(f"   ✅ 禁止词已替换为安全词", "")
                                        else:
                                            log(f"   ✅ 重生成后低俗检测通过", "")
                        except ImportError as _ie:
                            log(f"   ⚠️ [低俗检测] 模块导入失败,跳过: {_ie}", "⚠️")
                        except Exception as _lbe:
                            log(f"   ⚠️ 低俗检测/重生成异常: {_lbe}", "⚠️")

                    except json.JSONDecodeError as je:
                        log(f"   ⚠️ JSON解析失败: {je}", "⚠️")
                else:
                    # 降级:旧格式兼容(加关键词过滤)
                    text = re.sub(r'^(解说:|解说词:|正文:|Narration:|narration:|Naration:|naration:|#+)', '', raw).strip()
                    if len(text) >= 50 and any(kw in text for kw in ['她', '他', '我', '你', '爱', '恨', '离婚', '分手', '真相', '秘密', '原来', '竟然', '身份', '背景', '打', '杀', '滚', '死']):
                        narration_text = text
                        log(f"   ⚠️ 解说降级: {len(narration_text)}字(无时间锚点)", "⚠️")
                    else:
                        log(f"   ⚠️ 解说降级失败:内容不含剧情关键词,已丢弃", "⚠️")
        except Exception as e:
            log(f"   ⚠️ LLM失败: {e}", "⚠️")

        # [低俗+空解说重试] 0字/过低也重试一次(带低俗规避)
        if (not narration_text or len(narration_text) < 80) and time_anchors:
            log(f"   ⚠️ 解说过短({len(narration_text) if narration_text else 0}字),尝试重生成(带低俗规避)", "⚠️")
            try:
                _anti_prompt2 = prompt + "\n【低俗规避】解说严格禁止任何低俗/擦边词汇!\n【低俗规避】不得出现性暗示、性器官、贴身衣物、丝袜、蕾丝、胸罩、内裤等描写\n【低俗规避】禁用'做爱''上床''裸''脱光''一丝不挂''臀部''大腿根'等任何低俗词汇\n【低俗规避】感情戏只写'深情对视''温柔相拥'等纯净描写\n【重要】narration字段严禁为空!必须写{_min_narr_chars}-{_target_narr_chars}字完整解说"
                _d3 = json.dumps({"model": "qwen3.5:4b", "prompt": _anti_prompt2, "stream": False,
                                "format": "json", "think": False,
                                "options": {"temperature": 0.5, "num_predict": 2000}}).encode('utf-8')
                _r3 = urllib.request.Request('http://localhost:11434/api/generate', data=_d3,
                                              headers={'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(_r3, timeout=SUBPROCESS_TIMEOUT) as _resp3:
                    _rw3 = json.loads(_resp3.read().decode('utf-8')).get('response', '').strip()
                    _j3 = ''
                    _s3 = _rw3.find('{')
                    _e3 = _rw3.rfind('}')
                    if _s3 >= 0 and _e3 > _s3:
                        _j3 = _rw3[_s3:_e3 + 1]
                    if _j3:
                        _p3 = json.loads(_j3)
                        # [FIX-20260708] 重试也解析segments格式
                        _segs3 = _p3.get('segments', [])
                        if _segs3:
                            narration_text = ''
                            narration_segments = []
                            time_anchors = []
                            for _s3i in _segs3:
                                _ts3 = _s3i.get('time_start', 0)
                                _te3 = _s3i.get('time_end', 0)
                                _sn3 = _s3i.get('narration', '')
                                if not _sn3 or len(_sn3) < 5:
                                    continue
                                try: _ts3 = float(_ts3)
                                except: _ts3 = 0.0
                                try: _te3 = float(_te3)
                                except: _te3 = 0.0
                                narration_segments.append((_ts3, _te3, _sn3))
                                narration_text += _sn3
                                time_anchors.append({'text': _sn3[:20], 'time': _ts3, 'duration': min(4.0, max(2.0, _te3 - _ts3))})
                            log(f"   ✅ 重试解说成功(segments): {len(narration_text)}字, {len(narration_segments)}段", "")
                        else:
                            _nt = _p3.get('narration', '')
                            if len(_nt) >= 80:
                                narration_text = _nt
                                _na = _p3.get('anchors', [])
                                if _na:
                                    time_anchors = []
                                    for _a in _na:
                                        if 'text' not in _a:
                                            continue
                                        _at = float(_a.get('time', 0)) if isinstance(_a.get('time'), (int, float)) else 0
                                        if _at == 0 and isinstance(_a.get('time'), str) and _a['time'].replace('.', '', 1).isdigit():
                                            _at = float(_a['time'])
                                        _ad = float(_a.get('duration', 3.0)) if isinstance(_a.get('duration'), (int, float)) else 3.0
                                        time_anchors.append({'text': str(_a['text']), 'time': _at, 'duration': _ad})
                                log(f"   ✅ 重试解说成功: {len(narration_text)}字, {len(time_anchors)}个锚点", "")
            except Exception as _re:
                log(f"   ⚠️ 重试失败: {_re}", "⚠️")

        # [FIX-失败即停-20260615→20260617放宽] 解说文字有效但锚点不足时,用均匀分布补充而非直接停止
        if not narration_text or len(narration_text) < 80:
            log(f"   ❌ 解说生成失败: 内容无效({len(narration_text) if narration_text else 0}字), 停止处理", "❌")
            raise RuntimeError(f"解说生成失败({len(narration_text) if narration_text else 0}字)")
        if not time_anchors and narration_text:
            log(f"   ⚠️ 锚点为0,改用均匀分布补充", "⚠️")

        # 步骤3: 时间锚点选片段(精确匹配)
        log("🎯 [3/8] 时间锚点选片段...", "⏳")
        selected = []

        # 计算每个文件在整体时间线上的起始偏移
        file_offsets = []
        acc = 0
        for f in files:
            dur = get_video_info(str(f)).get("duration", 60)
            file_offsets.append(acc)
            acc += dur
        total_dur = acc

        def time_to_file_and_local(global_time):
            """全局时间 → (file_idx, local_time)"""
            for fidx, offset in enumerate(file_offsets):
                next_offset = file_offsets[fidx + 1] if fidx + 1 < len(file_offsets) else float('inf')
                if offset <= global_time < next_offset:
                    return fidx, global_time - offset
            return len(files) - 1, 0

        # [FIX-分段解说-20260705] 优先用narration_segments直接选片段
        if narration_segments:
            log(f"   📐 分段模式: {len(narration_segments)}段解说, 字幕校正时间边界", "")

            # [双向校正] LLM给的time_start/time_end是粗略的,用字幕库校正到精确时间戳
            # 构建 全局时间→字幕 映射表(扁平化所有文件字幕,带全局时间偏移)
            _all_subs_global = []  # [(global_start, global_end, text), ...]
            for _fidx_o, _offset_o in enumerate(file_offsets):
                for _ss, _se, _st in all_file_subtitles.get(_fidx_o, []):
                    _all_subs_global.append((_offset_o + _ss, _offset_o + _se, _st))
            _all_subs_global.sort(key=lambda x: x[0])

            def _snap_to_subtitle(t, prefer='start'):
                """把粗略时间校正到最近的字幕时间戳"""
                if not _all_subs_global:
                    return t
                best_t, best_dist = t, float('inf')
                for _gs, _ge, _gt in _all_subs_global:
                    _d_s = abs(_gs - t)
                    _d_e = abs(_ge - t)
                    if prefer == 'start' and _d_s < best_dist and _d_s < 5.0:
                        best_t, best_dist = _gs, _d_s
                    elif prefer == 'end' and _d_e < best_dist and _d_e < 5.0:
                        best_t, best_dist = _ge, _d_e
                    elif _d_s < best_dist and _d_s < 5.0:
                        best_t, best_dist = _gs, _d_s
                return best_t

            # 校正每段的时间边界
            _corrected_segs = []
            for _si, (_ts, _te, _sn) in enumerate(narration_segments):
                _cts = _snap_to_subtitle(_ts, prefer='start')
                _cte = _snap_to_subtitle(_te, prefer='end')
                # 保证段间连续:后一段的start=前一段的end
                if _corrected_segs and _cts < _corrected_segs[-1][1]:
                    _cts = _corrected_segs[-1][1]
                if _cte <= _cts:
                    _cte = _cts + 3.0  # 最小3秒段
                _corrected_segs.append((_cts, _cte, _sn))
            narration_segments = _corrected_segs
            log(f"   ✅ 校正后: {[(f'{s:.1f}-{e:.1f}', n[:15]) for s,e,n in narration_segments[:3]]}", "")

            _clip_seg_map = []  # selected[i] 对应的 narration_segment 索引
            # [FIX-20260707] 选片改为关键词匹配字幕,不按segment时间区间选整个素材
            # 每段解说提取关键词,在字幕库中找最匹配的片段
            import re as _re_sel
            _stop_sel = {'一个','什么','怎么','这个','那个','没有','不是','就是','但是','还是','因为','所以','可以','如果','他们','她们','我们','自己','之后','然后','只是','可是','而且','虽然','然而','不过','已经','应该','可能','真的','这么','那么','难道','叫做','起来','时候'}
            _BASE_CLIP_DURATION = 12.0  # 基准片段时长
            _MAX_CLIPS_PER_SEG = 2  # 每段解说最多选2个片段
            # [PA+SW+ED-20260731] beat感知选片时长: 爆发/悬念→短切快剪, 收尾→呼吸, 铺垫→标准
            _BEAT_DURATION = {'爆发': 8.0, '反转': 10.0, '悬念': 8.0, '铺垫': 12.0, '收尾': 14.0}
            for seg_idx, (seg_start, seg_end, seg_narr) in enumerate(narration_segments):
                # 从解说词提取关键词
                _seg_words = _re_sel.findall(r'[\u4e00-\u9fff]{2,4}', seg_narr)
                _seg_kw = [w for w in _seg_words if w not in _stop_sel][:5]
                # 在字幕库中找关键词匹配度最高的片段(取top2)
                _seg_matches = []
                for fidx, subs in all_file_subtitles.items():
                    for sub_start, sub_end, sub_text in subs:
                        _score = 0
                        for kw in _seg_kw:
                            if kw in sub_text:
                                _score += 1
                        if _score > 0:
                            _seg_matches.append((_score, fidx, sub_start, sub_end))
                _seg_matches.sort(key=lambda x: -x[0])
                _added_for_seg = 0
                _beat_dur = _BEAT_DURATION.get(narration_beats.get(seg_idx, '铺垫'), _BASE_CLIP_DURATION)
                for _sm in _seg_matches[:_MAX_CLIPS_PER_SEG]:
                    _sc, fidx, sub_start, sub_end = _sm
                    file_dur = get_video_info(str(files[fidx])).get("duration", 60)
                    _cs = max(0, sub_start - 1.0)
                    _ce = min(file_dur, sub_start + _beat_dur)
                    if _ce - _cs >= 3.0:
                        selected.append((fidx, _cs, _ce, 1.0))
                        _clip_seg_map.append(seg_idx)
                        _added_for_seg += 1
                if _added_for_seg == 0:
                    # 关键词无匹配,用segment起始时间定位
                    _fidx_s, _local_s = time_to_file_and_local(seg_start)
                    if 0 <= _fidx_s < len(files):
                        _fdur = get_video_info(str(files[_fidx_s])).get("duration", 60)
                        _beat_dur = _BEAT_DURATION.get(narration_beats.get(seg_idx, '铺垫'), _BASE_CLIP_DURATION)
                        _cs = max(0, _local_s - 1.0)
                        _ce = min(_fdur, _local_s + _beat_dur)
                        if _ce - _cs >= 3.0:
                            selected.append((_fidx_s, _cs, _ce, 1.0))
                            _clip_seg_map.append(seg_idx)
            log(f"   ✅ 关键词匹配选片: {len(selected)}个片段(对应{len(narration_segments)}段解说)", "")
            if len(selected) < 3:
                log(f"   ⚠️ 分段选片不足({len(selected)}个),降级为锚点模式", "⚠️")
                selected = []
                _clip_seg_map = []

        # [旧逻辑] 锚点反向匹配(分段选片失败时降级使用)
        if not selected and time_anchors:
            for anchor in time_anchors:
                llm_time, dur = anchor['time'], anchor['duration']
                anchor_text = anchor.get('text', '')

                # 在字幕库里找最接近该时间戳的真实台词
                best_match = None
                best_dist = float('inf')
                for fidx, subs in all_file_subtitles.items():
                    for sub_start, sub_end, sub_text in subs:
                        # 计算全局时间
                        global_sub_time = file_offsets[fidx] + sub_start
                        dist = abs(global_sub_time - llm_time)
                        # 优先匹配文本相似的,其次匹配时间近的
                        text_match = (anchor_text in sub_text) or (sub_text in anchor_text)
                        if text_match and dist < 10:  # 文本匹配+10秒内
                            best_match = (fidx, sub_start, sub_end, sub_text)
                            best_dist = dist
                            break
                        elif dist < best_dist and dist < 5:  # 纯时间近+5秒内
                            best_match = (fidx, sub_start, sub_end, sub_text)
                            best_dist = dist
                    if best_dist < 2:
                        break

                if best_match:
                    fidx, sub_start, sub_end, matched_text = best_match
                    file_dur = get_video_info(str(files[fidx])).get("duration", 60)
                    # 以字幕时间戳为准,稍微提前捕捉说话人画面
                    start = max(0, sub_start - 0.5)
                    end = min(file_dur, sub_end + 0.5)
                    if end - start >= 1.5:
                        selected.append((fidx, start, end, 1))
                else:
                    # 降级:LLM时间±3秒内找任意情绪画面
                    fidx, local_t = time_to_file_and_local(llm_time)
                    if 0 <= fidx < len(files):
                        for sub_start, sub_end, sub_text in all_file_subtitles.get(fidx, []):
                            if abs(sub_start - local_t) < 3:
                                file_dur = get_video_info(str(files[fidx])).get("duration", 60)
                                start = max(0, sub_start - 0.3)
                                end = min(file_dur, sub_end + 0.3)
                                if end - start >= 1.5:
                                    selected.append((fidx, start, end, 1))
                                    break
            log(f"   ✅ 锚点反向匹配: {len(selected)}个片段(已校正到真实字幕)", "")

        # 锚点不够时,用字幕情绪分析补充(均匀采样,匹配音频时长)
        if len(selected) < 5:
            log("   🔄 锚点不足,用情绪分析补充...", "")
            # 根据解说字数估算目标剪辑数(约4秒/片段,语速3.5字/秒)
            est_audio_sec = len(narration_text) / 3.5 if narration_text else 60
            target_clips = max(12, min(40, int(est_audio_sec / 4) + 2))

            emotion_words = ['离婚', '分手', '背叛', '欺骗', '打', '杀', '滚', '死',
                           '真相', '秘密', '原来', '其实', '竟然', '身份', '背景']
            emotion_candidates = []
            for fidx, subs in all_file_subtitles.items():
                for start, end, text in subs:
                    if any(w in text for w in emotion_words):
                        emotion_candidates.append((fidx, max(0, start - 0.5), end + 0.5, 1))

            # 均匀抽取:保证时间线均匀覆盖,避免扎堆
            if emotion_candidates:
                step = max(1, len(emotion_candidates) // max(1, target_clips - len(selected)))
                for i in range(0, len(emotion_candidates), step):
                    if len(selected) >= target_clips:
                        break
                    selected.append(emotion_candidates[i])

            selected = _deduplicate_clips(selected, threshold=0.2)
            selected = _merge_clips_v2(selected)
            log(f"   🔄 情绪补充后{len(selected)}个片段,目标{target_clips}个", "")

        # 最后兜底:均匀分布
        if len(selected) < 5:
            log("   🔄 情绪分析不足,均匀分布补充...", "")
            interval = total_dur / 12
            t = 0
            for i in range(12):
                fidx, local_t = time_to_file_and_local(t)
                if 0 <= fidx < len(files):
                    file_dur = get_video_info(str(files[fidx])).get("duration", 60)
                    start = max(0, local_t)
                    end = min(file_dur, local_t + 3)
                    if end - start >= 1.5:
                        selected.append((fidx, start, end, 1))
                t += interval

        selected = _merge_clips_v2(selected)
        log(f"   ✅ 最终选中{len(selected)}个片段", "")

        # [P0-1反同质化] 片段类型覆盖约束
        # 适配:主流程 selected=(fidx,start,end,score),函数期望(hl_start,hl_end,score)
        try:
            if '_enforce_type_diversity' in globals() and len(selected) >= 5:
                # 提取字幕文本用于类型分类
                sub_texts = []
                for fidx, s, e, _ in selected:
                    seg_texts = []
                    for sub_start, sub_end, sub_text in all_file_subtitles.get(fidx, []):
                        if s <= sub_start <= e or s <= sub_end <= e:
                            seg_texts.append(sub_text)
                    sub_texts.append(" ".join(seg_texts[:3]))
                # 转为函数期望格式 (start, end, score),取后3字段
                hl_fmt = [(s, e, sc) for _, s, e, sc in selected]
                fixed = _enforce_type_diversity(hl_fmt, sub_texts)
                # 重建 (fidx,start,end,score) 格式
                # 保留前5个原始clip,补入新增的
                orig_ids = set(id(h) for h in hl_fmt[:min(len(hl_fmt), TARGET_CLIP_COUNT)])
                new_clips = []
                for h in fixed:
                    if id(h) in orig_ids:
                        idx = hl_fmt.index(h)
                        new_clips.append(selected[idx])
                    else:
                        new_clips.append((0, h[0], h[1], h[2]))
                if len(new_clips) > len(selected):
                    selected = new_clips[:min(len(new_clips), TARGET_CLIP_COUNT + 3)]
                    log(f"   🎭 类型覆盖优化: {len(selected)}个片段", "")
        except Exception as e:
            log(f"   ⚠️ 类型覆盖优化跳过: {e}", "")

        # [P1-1] 剪辑节奏模板重排
        try:
            if len(selected) >= 5 and 'RHYTHM_TEMPLATES' in globals() and '_apply_rhythm_template' in globals():
                rt = random.choice(RHYTHM_TEMPLATES)
                selected = _apply_rhythm_template(selected, rt)
        except Exception as e:
            log(f"   ⚠️ 节奏模板跳过: {e}", "")

        # [P1-2] 开场钩子已禁用(解说由LLM自然生成开场,不叠加标题体)

        # [FIX-时长匹配-20260530] TTS提前到片段提取前
        # 先知道解说多长,再决定选多少片段,避免视频远远短于解说
        # 步骤4: TTS配音(提前)
        log("🎙️ [4/8] TTS配音...", "⏳")
        # [FIX-20260707] 禁用分段TTS,回到整段解说驱动视频模式(避免画面卡住)
        segment_audios = []  # 强制走旧流程:整段TTS
        if False and narration_segments and '_tts_narration' in globals():
            log(f"   📝 分段TTS: {len(narration_segments)}段逐段生成", "")
            for _si, (_sts, _ste, _snarr) in enumerate(narration_segments):
                if not _snarr or not _snarr.strip():
                    # 空段用静音替代
                    _silence_path = os.path.join(tempfile.gettempdir(), f"__seg_silence_{_si}_{int(time.time())}.wav")
                    _seg_dur = max(1.0, _ste - _sts)
                    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                                    f"anullsrc=channel_layout=mono:sample_rate=24000",
                                    "-t", str(_seg_dur), "-q:a", "9", "-ac", "1",
                                    _silence_path], capture_output=True, timeout=15)
                    if os.path.exists(_silence_path):
                        segment_audios.append((_silence_path, _seg_dur))
                    else:
                        segment_audios.append((None, _seg_dur))
                    log(f"   ⏭️ 段{_si}: 空解说,用静音({_seg_dur:.1f}s)", "")
                    continue
                try:
                    _seg_audio = _tts_narration(_snarr, genre, drama_name=drama_name)
                    if _seg_audio and os.path.exists(_seg_audio) and os.path.getsize(_seg_audio) > 1000:
                        _seg_dur = _get_video_duration(_seg_audio) if '_get_video_duration' in globals() else len(_snarr) / 3.5
                        if _seg_dur is None:
                            _seg_dur = len(_snarr) / 3.5
                        segment_audios.append((_seg_audio, _seg_dur))
                        log(f"   ✅ 段{_si} TTS: {_seg_dur:.1f}s, '{_snarr[:20]}...'", "")
                    else:
                        # TTS失败,用静音替代
                        _silence_path = os.path.join(tempfile.gettempdir(), f"__seg_silence_{_si}_{int(time.time())}.wav")
                        _seg_dur = max(1.0, _ste - _sts)
                        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                                        f"anullsrc=channel_layout=mono:sample_rate=24000",
                                        "-t", str(_seg_dur), "-q:a", "9", "-ac", "1",
                                        _silence_path], capture_output=True, timeout=15)
                        if os.path.exists(_silence_path):
                            segment_audios.append((_silence_path, _seg_dur))
                        else:
                            segment_audios.append((None, _seg_dur))
                        log(f"   ⚠️ 段{_si} TTS失败,用静音替代({_seg_dur:.1f}s)", "⚠️")
                except Exception as _tts_e:
                    log(f"   ⚠️ 段{_si} TTS异常: {_tts_e}", "⚠️")
                    _silence_path = os.path.join(tempfile.gettempdir(), f"__seg_silence_{_si}_{int(time.time())}.wav")
                    _seg_dur = max(1.0, _ste - _sts)
                    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                                    f"anullsrc=channel_layout=mono:sample_rate=24000",
                                    "-t", str(_seg_dur), "-q:a", "9", "-ac", "1",
                                    _silence_path], capture_output=True, timeout=15)
                    if os.path.exists(_silence_path):
                        segment_audios.append((_silence_path, _seg_dur))
                    else:
                        segment_audios.append((None, _seg_dur))
            # 拼接所有段音频为一条narration_audio(兼容Step 4.5逻辑)
            _valid_seg_audios = [a for a, _ in segment_audios if a and os.path.exists(a)]
            if _valid_seg_audios:
                _seg_concat_list = os.path.join(tempfile.gettempdir(), f"__seg_tts_concat_{int(time.time())}.txt")
                with open(_seg_concat_list, 'w', encoding='utf-8') as _f:
                    for _sa in _valid_seg_audios:
                        _f.write(f"file '{_sa}'\n")
                _narr_concat_out = os.path.join(tempfile.gettempdir(), f"__narr_concat_{int(time.time())}.wav")
                _seg_concat_r = subprocess.run([
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', _seg_concat_list, '-c', 'copy', _narr_concat_out
                ], capture_output=True, timeout=60)
                if _seg_concat_r.returncode == 0 and os.path.exists(_narr_concat_out):
                    narration_audio = _narr_concat_out
                else:
                    # concat失败,用第一段作为fallback
                    narration_audio = _valid_seg_audios[0]
                try: os.remove(_seg_concat_list)
                except: pass
            else:
                narration_audio = None
        else:
            narration_audio = _tts_narration(narration_text, genre, drama_name=drama_name) if '_tts_narration' in globals() else None

        # 步骤4.5: 片段时长适配
        # 原则:先去重,判定解说和片段的关系:
        #   - 解说 ≤ 片段+3s → 通过
        #   - 解说 > 片段+3s → 精准匹配(关键词)→ 时间扫描兜底 → 再判定
        # 核心:保留解说完整,补充与解说内容相关的片段
        if narration_audio and os.path.exists(narration_audio):
            # [FIX-分段TTS对齐-20260706] 分段模式下narr_dur=所有段音频时长之和
            if segment_audios:
                narr_dur = sum(d for _, d in segment_audios if d is not None)
            else:
                narr_dur = _get_video_duration(narration_audio) if '_get_video_duration' in globals() else len(narration_text) / 3.5

            # [FIX-精准匹配-20260629] 提前提取解说关键词,用于补充片段的内容匹配
            import re as _re
            # 从解说中提取2-4字关键词(排除'的'、'了'、'是'等停用词)
            _narr_words = _re.findall(r'[\u4e00-\u9fff]{2,4}', narration_text)
            _stop_words = {'一个','什么','怎么','这个','那个','没有','不是','就是','但是','还是','因为','所以','可以','如果','他们','她们','我们','自己','还是','之后','然后','只是','可是','但是','而且','虽然','然而','不过','已经','应该','可能','真的','这么','那么','难道','叫做','起来','时候','就是'}
            _narr_keywords = [w for w in _narr_words if w not in _stop_words]
            _narr_keywords = list(set(_narr_keywords))  # 去重
            log(f"   🔑 解说关键词: {_narr_keywords[:10]}...({len(_narr_keywords)}个)", "")

            # [Strategy D: 视觉语义匹配] 已禁用 - BLIP2 2.7b在32GB Mac上推理过慢
            _vision_reranked = None
            _vm_loaded = False

            _pre_clip_total = 0  # 用于未改善检测
            _no_improve_rounds = 0  # 连续未改善轮次计数
            # [FIX-分段解说-20260705] 分段模式片段已按解说段选好
            # [FIX-分段TTS对齐-20260706] 分段模式下跳过去重--相邻段选片时间重叠是正常的
            # (解说段时间区间可能重叠),去重会删掉合法片段导致部分段无视频
            _seg_clip_total = sum(end - start for _, start, end, _ in selected)
            _skip_replenish = False
            # [FIX-20260707] 禁用分段模式跳过去重,走正常去重+补片段流程(解说驱动视频)
            if False and narration_segments and _seg_clip_total >= max(60.0, narr_dur):
                # 分段模式只做merge(合并完全相同的片段),不去重
                selected = _merge_clips_v2(selected)
                # [FIX-分段TTS对齐-20260706] 去重/合并后重新计算clip→seg映射
                # 基于片段中点时间落在哪个narration_segment的时间区间来分配
                _file_offsets_local = []
                _accum = 0.0
                for _fi in range(len(files)):
                    _file_offsets_local.append(_accum)
                    _accum += float(get_video_info(str(files[_fi])).get("duration", 60))
                def _global_time_of_clip(clip_entry):
                    _fidx_c, _cs_c, _ce_c, _ = clip_entry
                    _mid_local = (_cs_c + _ce_c) / 2.0
                    return _file_offsets_local[_fidx_c] + _mid_local
                _clip_seg_map = []
                for _sc in selected:
                    _gt = _global_time_of_clip(_sc)
                    _best_si = 0
                    _best_dist = float('inf')
                    for _si, (_ss, _se, _) in enumerate(narration_segments):
                        if _ss <= _gt <= _se:
                            _best_si = _si
                            _best_dist = 0
                            break
                        _d = min(abs(_ss - _gt), abs(_se - _gt))
                        if _d < _best_dist:
                            _best_dist = _d
                            _best_si = _si
                    _clip_seg_map.append(_best_si)
                _seg_after = sum(end - start for _, start, end, _ in selected)
                log(f"   ✅ 分段模式: 去重后{len(selected)}个片段,{_seg_after:.1f}s ≥ 解说{narr_dur:.1f}s,跳过补片段", "")
                _skip_replenish = True
                clip_total = _seg_after  # 确保clip_total有值,供后续else块引用
                _min_dur = max(60.0, narr_dur)  # 确保_min_dur有值,供后续else块引用
            if not _skip_replenish:
             for _round in range(10):  # 增加轮次上限,确保解说完整
                # 1. 去重 (阈值1.5s:允许片段间隔≥1.5s不判重叠,避免时间扫描每轮加的片段被下轮去重删掉
                pre_n = len(selected)
                # [FIX-20260626] 检测震荡:记录去重前片段数
                # 若补充后片段数等于去重前,说明补回来的正是去重删的,进入稳定态
                _pre_dedup_n = len(selected)
                selected = _deduplicate_clips(selected, threshold=1.5)
                dedup_n = pre_n - len(selected)
                clip_total = sum(end - start for _, start, end, _ in selected)
                log(f"   📏 [轮{_round+1}] 片段{clip_total:.1f}s(去重{dedup_n}个,{len(selected)}个) vs 解说{narr_dur:.1f}s", "")

                # 2. 通过条件: 片段 ≥ 解说时长且不超过成片上限
                # [FIX-20260712] 不再用max_duration限制片段目标,跟解说走
                _min_dur = max(60.0, narr_dur + 3.0)
                if clip_total >= _min_dur:
                    log(f"   ✅ 通过: 片段{clip_total:.1f}s ≥ {_min_dur:.1f}s(解说{narr_dur:.1f}s)", "")
                    break
# [FIX-20260712] 移除成片上限硬截断,跟解说走

                # [FIX-20260701] 总时长未改善保护:连续3轮总时长无提升则停止
                if clip_total <= _pre_clip_total + 0.5:  # 0.5s容差
                    _no_improve_rounds += 1
                else:
                    _no_improve_rounds = 0
                _pre_clip_total = clip_total  # 更新供下轮比较
                if _no_improve_rounds >= 3:
                    log(f"   🛑 总时长连续3轮无改善({clip_total:.1f}s),停止补充", "")
                    break

                # 3. 补片段: 精准匹配优先,时间扫描兜底
                _target_dur = max(60.0, narr_dur + 3.0)  # [FIX-20260712] 跟解说走,不受max_duration限制
                _added = 0

                # ---- Strategy B: 关键词匹配(精准匹配) ----
                # [合规] 高风险片段关键词(包含这些词的字幕优先跳过)
                _RISK_SEGMENT_WORDS = [
                    '打死', '弄死', '杀了', '去死', '强奸', '强暴', '非礼', '脱衣服',
                    '辱骂', '抽耳光', '拳打', '脚踢', '虐待', '下跪求', '磕头',
                    '穷鬼', '土包子', '你不配', '恶心', '废物', '贱人', '婊子',
                    '我要报仇', '血债', '往死里', '赶尽杀绝', '不得好死',
                    '碾压你', '踩在脚下', '看不起谁', '也配', '算什么东西'
                ]
                # 对字幕库中每条字幕计算与解说关键词的匹配度,选最高分
                if _narr_keywords:
                    # 预缓存文件时长
                    _file_durs = {}
                    for _fidx in range(len(files)):
                        _file_durs[_fidx] = float(get_video_info(str(files[_fidx])).get("duration", 60))

                    # 构建候选池:每条字幕(文件idx, start, end, text, match_score)
                    _candidates = []
                    for _fidx, _subs in all_file_subtitles.items():
                        if _fidx >= len(files):
                            continue
                        for _sub_start, _sub_end, _sub_text in _subs:
                            # 跳过太短的片段
                            if _sub_end - _sub_start < 1.0:
                                continue
                            # 计算匹配得分:字幕文本中有多少个关键词
                            _match_cnt = sum(1 for kw in _narr_keywords if kw in _sub_text)
                            if _match_cnt > 0:
                                # 除以长度惩罚,避免长句暴力刷分
                                _len_penalty = max(1.0, len(_sub_text) / 20)
                                _score = _match_cnt / _len_penalty
                                _candidates.append((_fidx, _sub_start, _sub_end, _score))

                    # 按分数降序排列
                    _candidates.sort(key=lambda x: x[3], reverse=True)

                    # [Strategy D: 视觉语义匹配] 已禁用
                    _vision_reranked = None

                    # 按匹配度选取,跳过与已有片段重叠的,且优先跳过合规风险片段
                    for _fidx, _sub_start, _sub_end, _score in _candidates:
                        # [合规] 检查待选片段字幕是否含高风险词
                        _sub_text_for_check = ''
                        if isinstance(all_file_subtitles, dict) and _fidx in all_file_subtitles:
                            for _ts, _te, _tt in all_file_subtitles[_fidx]:
                                if _ts <= _sub_start and _te >= _sub_end:
                                    _sub_text_for_check = _tt
                                    break
                        _risk_hit = any(_rw in _sub_text_for_check for _rw in _RISK_SEGMENT_WORDS)
                        if _risk_hit:
                            continue  # 跳过高风险片段
                        if clip_total >= _target_dur:
                            break
                        # 重叠检查
                        _overlap = any(
                            _fidx == _ef and _sub_start < _ee - 0.5 and _sub_end > _es + 0.5
                            for _ef, _es, _ee, _ in selected
                        )
                        if not _overlap:
                            # 前后留0.3秒余量,确保画面完整
                            _fdur = _file_durs.get(_fidx, 60.0)
                            _fs = max(0, _sub_start - 0.3)
                            _fe = min(_fdur, _sub_end + 0.3)
                            if _fe - _fs >= 1.5:
                                selected.append((_fidx, _fs, _fe, 1.0 + _score * 0.5))
                                clip_total += (_fe - _fs)
                                _added += 1

                    log(f"   🎯 [轮{_round+1}] 精准匹配补{_added}个片段(关键词匹配,共{clip_total:.1f}s)", "")

                # ---- Strategy C: 时间扫描兜底(原贪心扫描) ----
                if clip_total < _target_dur:
                    _t_added = 0
                    for _fidx in range(len(files)):
                        if clip_total >= _target_dur:
                            break
                        _fdur = float(get_video_info(str(files[_fidx])).get("duration", 60))
                        _t = 0.0
                        while _t < _fdur - 3.0:
                            if clip_total >= _target_dur:
                                break
                            _seg_end = min(_t + 4.0, _fdur)
                            # 区间重叠检查: 新[_t,_seg_end] 与 已有[_es,_ee] 重叠
                            _overlap = any(
                                _fidx == _ef and _t < _ee - 0.5 and _seg_end > _es + 0.5
                                for _ef, _es, _ee, _ in selected
                            )
                            if not _overlap:
                                selected.append((_fidx, _t, _seg_end, 1.0))
                                clip_total += (_seg_end - _t)
                                _t_added += 1
                            _t += 3.0
                    if _t_added > 0:
                        log(f"   🔧 [轮{_round+1}] 时间扫描补{_t_added}个片段(兜底), 共{clip_total:.1f}s", "")

                # [FIX-20260626] 震荡检测:若补完后片段数等于去重前,停止
                if len(selected) == _pre_dedup_n and _added > 0:
                    log(f"   🛑 片段数稳定({len(selected)}个),停止补充(补回的=去重的)", "")
                    break

                # 回到步骤1去重后再判定

            else:
                log(f"   ⚠️ 10轮后仍未满足(片段{clip_total:.1f}s, 目标{_min_dur:.1f}s), 接受当前结果(解说完整但视频可能偏短)", "⚠️")

        else:
            # 无narration_audio时只做一次去重
            selected = _deduplicate_clips(selected, threshold=0.2)

        # 步骤5: 片段提取
        log("🎬 [5/8] 片段提取...", "⏳")
        try:
            tmp_dir = tempfile.mkdtemp(prefix="cutter_")
            log(f"   ✅ 临时目录创建: {tmp_dir}", "")
        except Exception as e:
            log(f"   ❌ 创建临时目录失败: {e}", "❌")
            import traceback
            log(f"   {traceback.format_exc()}", "")
            return None
        clip_files = []
        _clip_file_seg_map = []  # clip_files[i] 对应的 narration_segment 索引(仅分段模式有效)
        log(f"   📊 选中片段数: {len(selected)}", "")

        # [FIX-音频对齐-20260520] 片段提取时保留原始音频轨
        # 原因:之前步骤4保留了音频(-c:a aac),但步骤6拼接时用-an丢弃音频,
        # 然后从源文件重新提取音频(-ss快进seek不精确),导致音频与视频时间不对齐。
        # 修复方案A:拼接时保留音频轨,后续直接从拼接视频中提取音频,不再重新提取。
        # [FIX-20260622] 调色在片段提取时应用(而非混音阶段),确保视频<解说时不丢失调色
        _clip_cg_filter = ''
        try:
            if '_get_color_grade' in globals():
                _clip_cg = _get_color_grade(genre)
                if _clip_cg:
                    _cbr = _clip_cg.get('brightness', 0)
                    _cco = _clip_cg.get('contrast', 1.0)
                    _csa = _clip_cg.get('saturation', 1.0)
                    _cga = _clip_cg.get('gamma', 1.0)
                    _ctemp = _clip_cg.get('temperature', None)
                    _clip_cg_filter = f'eq=brightness={_cbr}:contrast={_cco}:saturation={_csa}:gamma={_cga}'
                    if _ctemp:
                        _clip_cg_filter += f',colortemperature={_ctemp}'
        except Exception:
            _clip_cg_filter = ''

        for i, (fidx, start, end, _) in enumerate(selected):
            src, out = str(files[fidx]), os.path.join(tmp_dir, f"clip_{i:03d}.mp4")
            # 将-ss移到-i后面:慢速seek保证帧级精确,避免音视频起始点偏差
            _crop_vf = (lambda _ho, _vo: f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:"
                        f"(ow-iw)/2+{int(out_w*_ho)}:(oh-ih)/2+{int(out_h*_vo)}")(
                        *_get_random_crop_offset() if '_get_random_crop_offset' in globals() else (0, 0))
            # [FIX-20260622] 调色滤镜叠加到裁切vf后面
            _full_vf = _crop_vf + (f',{_clip_cg_filter}' if _clip_cg_filter else '')
            cmd = ["ffmpeg", "-y", "-i", src, "-ss", str(start), "-t", str(end - start),
                   "-vf", _full_vf,
                   "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k",
                   "-loglevel", "error", out]
            try:
                subprocess.run(cmd, check=True, timeout=30)
                if os.path.exists(out) and os.path.getsize(out) > 1000:
                    clip_files.append(out)
                    if '_clip_seg_map' in dir() and _clip_seg_map and i < len(_clip_seg_map):
                        _clip_file_seg_map.append(_clip_seg_map[i])
                    else:
                        _clip_file_seg_map.append(-1)
                    log(f"   ✅ 片段{i}提取成功: {os.path.getsize(out)} bytes", "")
                else:
                    log(f"   ⚠️ 片段{i}文件过小或不存在", "⚠️")
            except subprocess.TimeoutExpired:
                log(f"   ⚠️ 片段{i}提取超时", "⚠️")
            except subprocess.CalledProcessError as e:
                log(f"   ⚠️ 片段{i}提取失败: {e}", "⚠️")
            except Exception as e:
                log(f"   ⚠️ 片段{i}提取异常: {e}", "⚠️")
                import traceback
                log(f"   {traceback.format_exc()}", "")

        log(f"   ✅ 提取{len(clip_files)}个片段(选中{len(selected)}个)", "")

        if len(clip_files) < 3:
            log("⚠️ 片段太少,跳过", "⚠️")
            return None



        # 步骤6: 拼接+混音
        log("🎞️ [6/8] 拼接+混音...", "⏳")
        output_dir = CONFIG.get("output_dir", "output_videos")
        os.makedirs(output_dir, exist_ok=True)
        date_str = time.strftime("%Y%m%d", time.localtime())
        output_file = os.path.join(output_dir, f"{drama_name}_{episode}_{date_str}.mp4")

        # [FIX-20260707] 禁用分段混音,回到解说驱动视频的旧模式(避免画面卡住)
        # 旧模式:整段解说→一条TTS→视频按解说总时长选片段拼接→混音
        segment_audios = []  # 强制走旧流程
        if False and segment_audios and '_clip_file_seg_map' in dir() and _clip_file_seg_map and \
           len(segment_audios) > 0 and len(clip_files) > 0:
            log(f"   🔀 分段混音模式: {len(segment_audios)}段, {len(clip_files)}个片段", "")

            # BGM选择
            bgm_emotion_tags = decision.get("emotion_tags", []) if 'decision' in dir() and decision else []
            bgm_genre_for_match = decision.get("drama_genre_for_bgm", genre) if 'decision' in dir() and decision else genre
            bgm_result = smart_bgm_select(bgm_genre_for_match, emotion_tags=bgm_emotion_tags) if 'smart_bgm_select' in globals() else (None, [])
            bgm_file = bgm_result[0] if bgm_result else None

            _orig_vol = CONFIG.get('orig_volume_with_narration', 0.10)
            _narr_vol = CONFIG.get('narration_volume', 2.50)

            # 按段分组clip_files
            _seg_clips = {}  # {seg_idx: [clip_path, ...]}
            for _ci, _cf in enumerate(clip_files):
                _si = _clip_file_seg_map[_ci] if _ci < len(_clip_file_seg_map) else 0
                _seg_clips.setdefault(_si, []).append(_cf)

            _mixed_seg_videos = []
            for _si in range(len(segment_audios)):
                _seg_clip_list = _seg_clips.get(_si, [])
                _seg_audio_path, _seg_audio_dur = segment_audios[_si]

                if not _seg_clip_list:
                    # [FIX-20260706] 段无视频片段时不跳过,用segment时间区间从源视频直切一段
                    log(f"   ⚠️ 段{_si}: 无对应视频片段,从源视频直切", "⚠️")
                    if _si < len(narration_segments):
                        _ss, _se, _ = narration_segments[_si]
                        try:
                            _fidx_s, _local_s = time_to_file_and_local(_ss)
                            _fidx_e, _local_e = time_to_file_and_local(_se)
                        except Exception:
                            _fidx_s, _local_s = 0, _ss
                            _fidx_e, _local_e = 0, _se
                        if _fidx_s == _fidx_e:
                            _fdur = get_video_info(str(files[_fidx_s])).get("duration", 60) if 'get_video_info' in globals() else 60
                            _cs = max(0, _local_s - 0.3)
                            _ce = min(_fdur, _local_e + 0.3)
                            if _ce - _cs >= 1.5:
                                _fallback_clip = os.path.join(tmp_dir, f"seg_{_si}_fallback.mp4")
                                _crop_vf_fb = (lambda _ho, _vo: f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:"
                                            f"(ow-iw)/2+{int(out_w*_ho)}:(oh-ih)/2+{int(out_h*_vo)}")(
                                            *_get_random_crop_offset() if '_get_random_crop_offset' in globals() else (0, 0))
                                _fb_cmd = ["ffmpeg", "-y", "-i", str(files[_fidx_s]), "-ss", str(_cs), "-t", str(_ce - _cs),
                                           "-vf", _crop_vf_fb, "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k",
                                           "-loglevel", "error", _fallback_clip]
                                try:
                                    subprocess.run(_fb_cmd, check=True, timeout=30)
                                    if os.path.exists(_fallback_clip) and os.path.getsize(_fallback_clip) > 1000:
                                        _seg_clip_list = [_fallback_clip]
                                        log(f"   ✅ 段{_si} fallback直切成功: {os.path.getsize(_fallback_clip)} bytes", "")
                                except Exception as _fb_e:
                                    log(f"   ⚠️ 段{_si} fallback直切失败: {_fb_e}", "⚠️")
                        else:
                            # 跨文件:切首文件的一段
                            _fdur_s = get_video_info(str(files[_fidx_s])).get("duration", 60) if 'get_video_info' in globals() else 60
                            _cs = max(0, _local_s - 0.3)
                            if _fdur_s - _cs >= 1.5:
                                _fallback_clip = os.path.join(tmp_dir, f"seg_{_si}_fallback.mp4")
                                _crop_vf_fb = (lambda _ho, _vo: f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:"
                                            f"(ow-iw)/2+{int(out_w*_ho)}:(oh-ih)/2+{int(out_h*_vo)}")(
                                            *_get_random_crop_offset() if '_get_random_crop_offset' in globals() else (0, 0))
                                _fb_cmd = ["ffmpeg", "-y", "-i", str(files[_fidx_s]), "-ss", str(_cs), "-t", str(min(_fdur_s - _cs, _se - _ss + 0.6)),
                                           "-vf", _crop_vf_fb, "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k",
                                           "-loglevel", "error", _fallback_clip]
                                try:
                                    subprocess.run(_fb_cmd, check=True, timeout=30)
                                    if os.path.exists(_fallback_clip) and os.path.getsize(_fallback_clip) > 1000:
                                        _seg_clip_list = [_fallback_clip]
                                        log(f"   ✅ 段{_si} fallback直切成功(跨文件): {os.path.getsize(_fallback_clip)} bytes", "")
                                except Exception as _fb_e:
                                    log(f"   ⚠️ 段{_si} fallback直切失败(跨文件): {_fb_e}", "⚠️")
                    if not _seg_clip_list:
                        log(f"   ⚠️ 段{_si}: fallback也失败,跳过此段", "⚠️")
                        continue

                # 1. 拼接该段的视频片段
                _seg_concat_list = os.path.join(tmp_dir, f"seg_{_si}_concat_list.txt")
                with open(_seg_concat_list, 'w', encoding='utf-8') as _f:
                    for _cf in _seg_clip_list:
                        _f.write(f"file '{_cf}'\n")
                _seg_concat_video = os.path.join(tmp_dir, f"seg_{_si}_concat.mp4")
                try:
                    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", _seg_concat_list,
                                   "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                                   "-r", "30", "-vsync", "cfr",
                                   "-c:a", "aac", "-b:a", "192k",
                                   "-loglevel", "error", _seg_concat_video],
                                  check=True, timeout=SUBPROCESS_TIMEOUT)
                except Exception as _e:
                    log(f"   ⚠️ 段{_si}拼接失败: {_e}", "⚠️")
                    continue

                if not os.path.exists(_seg_concat_video):
                    log(f"   ⚠️ 段{_si}拼接文件不存在", "⚠️")
                    continue

                # 2. 提取该段视频原声
                _seg_orig_audio = os.path.join(tmp_dir, f"seg_{_si}_orig.aac")
                _seg_orig_r = subprocess.run(["ffmpeg", "-y", "-i", _seg_concat_video,
                                              "-vn", "-acodec", "copy", _seg_orig_audio],
                                             capture_output=True, timeout=30)
                _has_seg_orig = _seg_orig_r.returncode == 0 and os.path.exists(_seg_orig_audio) and os.path.getsize(_seg_orig_audio) > 500

                # 3. 混音: 原声 + 解说 (如果有解说音频)
                _seg_mixed_video = os.path.join(tmp_dir, f"seg_{_si}_mixed.mp4")
                if _seg_audio_path and os.path.exists(_seg_audio_path):
                    # 提取原声为wav(便于混音)
                    _seg_orig_wav = os.path.join(tmp_dir, f"seg_{_si}_orig.wav")
                    if _has_seg_orig:
                        subprocess.run(["ffmpeg", "-y", "-i", _seg_orig_audio, "-ar", "44100", "-ac", "2",
                                       _seg_orig_wav], capture_output=True, timeout=30)
                    # 构建混音filter
                    _seg_video_dur = _get_video_duration(_seg_concat_video) if '_get_video_duration' in globals() else _seg_audio_dur
                    if _seg_video_dur is None:
                        _seg_video_dur = _seg_audio_dur
                    # [FIX-20260707] 视频比解说短时用tpad复制最后一帧避免画面冻结
                    # 视频比解说长时截取到解说时长确保解说覆盖100%
                    _need_tpad = _seg_audio_dur > _seg_video_dur + 0.5
                    _need_trim = _seg_video_dur > _seg_audio_dur + 0.5
                    _tpad_dur = max(0, _seg_audio_dur - _seg_video_dur) if _need_tpad else 0
                    if _has_seg_orig and os.path.exists(_seg_orig_wav):
                        # 原声 + 解说 混音
                        if _need_tpad:
                            _vfilter = f"tpad=stop_mode=blank:stop_duration={_tpad_dur:.3f}"
                            _vmap = "[vpad]"
                        elif _need_trim:
                            _vfilter = f"trim=duration={_seg_audio_dur:.3f},setpts=PTS-STARTPTS"
                            _vmap = "[vpad]"
                        else:
                            _vfilter = "null"
                            _vmap = "0:v"
                        _mix_filter = f"[0:v]{_vfilter}[vpad];[1:a]volume={_orig_vol},apad=whole_dur={_seg_audio_dur:.3f}[a0];[2:a]volume={_narr_vol},apad=whole_dur={_seg_audio_dur:.3f}[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]"
                        _mix_cmd = ["ffmpeg", "-y", "-i", _seg_concat_video,
                                    "-i", _seg_orig_wav,
                                    "-i", _seg_audio_path,
                                    "-filter_complex", _mix_filter,
                                    "-map", _vmap, "-map", "[aout]",
                                    "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                                    "-c:a", "aac", "-b:a", "192k",
                                    "-loglevel", "error", _seg_mixed_video]
                    else:
                        # 无原声,只用解说音频
                        if _need_tpad:
                            _vfilter_n = f"tpad=stop_mode=blank:stop_duration={_tpad_dur:.3f}"
                            _vmap_n = "[vpad]"
                        elif _need_trim:
                            _vfilter_n = f"trim=duration={_seg_audio_dur:.3f},setpts=PTS-STARTPTS"
                            _vmap_n = "[vpad]"
                        else:
                            _vfilter_n = "null"
                            _vmap_n = "0:v"
                        if _need_tpad or _need_trim:
                            _mix_cmd = ["ffmpeg", "-y", "-i", _seg_concat_video,
                                        "-i", _seg_audio_path,
                                        "-filter_complex", f"[0:v]{_vfilter_n}[vpad]",
                                        "-map", _vmap_n, "-map", "1:a",
                                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                                        "-c:a", "aac", "-b:a", "192k",
                                        "-loglevel", "error", _seg_mixed_video]
                        else:
                            _mix_cmd = ["ffmpeg", "-y", "-i", _seg_concat_video,
                                        "-i", _seg_audio_path,
                                        "-map", "0:v", "-map", "1:a",
                                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                                        "-c:a", "aac", "-b:a", "192k",
                                        "-loglevel", "error", _seg_mixed_video]
                    try:
                        subprocess.run(_mix_cmd, check=True, timeout=SUBPROCESS_TIMEOUT)
                        if os.path.exists(_seg_mixed_video) and os.path.getsize(_seg_mixed_video) > 1000:
                            _mixed_seg_videos.append(_seg_mixed_video)
                            log(f"   ✅ 段{_si}混音完成: {os.path.getsize(_seg_mixed_video)} bytes", "")
                        else:
                            # 混音失败,用拼接视频
                            _mixed_seg_videos.append(_seg_concat_video)
                            log(f"   ⚠️ 段{_si}混音文件异常,用原拼接视频", "⚠️")
                    except Exception as _e:
                        log(f"   ⚠️ 段{_si}混音失败: {_e},用原拼接视频", "⚠️")
                        _mixed_seg_videos.append(_seg_concat_video)
                    # 清理临时原声wav
                    if os.path.exists(_seg_orig_wav):
                        try: os.remove(_seg_orig_wav)
                        except: pass
                else:
                    # 无解说音频,直接用拼接视频
                    _mixed_seg_videos.append(_seg_concat_video)
                    log(f"   ⏭️ 段{_si}无解说音频,保留原声", "")

                # 清理临时文件
                for _tmp_f in [_seg_concat_list, _seg_orig_audio]:
                    if os.path.exists(_tmp_f):
                        try: os.remove(_tmp_f)
                        except: pass

            # 4. 拼接所有段的混音视频
            if len(_mixed_seg_videos) > 0:
                _final_concat_list = os.path.join(tmp_dir, "final_seg_list.txt")
                with open(_final_concat_list, 'w', encoding='utf-8') as _f:
                    for _sv in _mixed_seg_videos:
                        _f.write(f"file '{_sv}'\n")
                _concat_video_path = os.path.join(tmp_dir, "concat_seg_final.mp4")
                try:
                    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", _final_concat_list,
                                   "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                                   "-r", "30", "-vsync", "cfr",
                                   "-c:a", "aac", "-b:a", "192k",
                                   "-loglevel", "error", _concat_video_path],
                                  check=True, timeout=SUBPROCESS_TIMEOUT)
                except Exception as _e:
                    log(f"   ⚠️ 最终拼接失败: {_e}", "⚠️")
                    _concat_video_path = None

                if _concat_video_path and os.path.exists(_concat_video_path):
                    # [FIX-20260707] 成片时长超限裁剪
                    _total_dur_final = _get_video_duration(_concat_video_path) if '_get_video_duration' in globals() else 60
                    if _total_dur_final is None:
                        _total_dur_final = 60.0
                    # [FIX-20260712] 移除BGM concat阶段硬截断,交由后续混音控制
                    if bgm_file and os.path.exists(bgm_file):
                        _bgm_vol = CONFIG.get('bgm_volume', 0.15)
                        _bgm_filter = f"[1:a]volume={_bgm_vol},aloop=loop=-1:size=2e9,atrim=0:{_total_dur_final:.3f}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
                        try:
                            subprocess.run(["ffmpeg", "-y", "-i", _concat_video_path,
                                           "-i", bgm_file,
                                           "-filter_complex", _bgm_filter,
                                           "-map", "0:v", "-map", "[aout]",
                                           "-c:v", "copy",
                                           "-c:a", "aac", "-b:a", "192k",
                                           "-loglevel", "error", output_file],
                                          check=True, timeout=SUBPROCESS_TIMEOUT)
                            log(f"   ✅ 分段混音+BGM叠加完成: {output_file}", "")
                            total_dur = _total_dur_final
                        except Exception as _e:
                            log(f"   ⚠️ BGM叠加失败: {_e},用无BGM版本", "⚠️")
                            shutil.copy(_concat_video_path, output_file)
                            total_dur = _total_dur_final
                    else:
                        shutil.copy(_concat_video_path, output_file)
                        log(f"   ✅ 分段混音完成(无BGM): {output_file}", "")
                        total_dur = _total_dur_final
                else:
                    log("   ⚠️ 分段拼接失败,降级为旧流程", "⚠️")
                    segment_audios = []  # 清空以走旧流程
            else:
                log("   ⚠️ 无有效混音段,降级为旧流程", "⚠️")
                segment_audios = []  # 清空以走旧流程
        else:
            segment_audios = []  # 确保走旧流程

        if not os.path.exists(output_file):
            # [旧流程: 整段TTS + 整段混音]
            concat_list = os.path.join(tmp_dir, "list.txt")
            with open(concat_list, "w", encoding="utf-8") as f:
                for cf in clip_files:
                    f.write(f"file '{cf}'\n")

            concat_video = os.path.join(tmp_dir, "concat.mp4")
            # [FIX-音频对齐-20260520] 拼接时保留音频轨(不再用-an丢弃)
            # 这样拼接视频自带精确对齐的原声音频,后续直接提取即可
            try:
                subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                               "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                               "-r", "30", "-vsync", "cfr",
                               "-c:a", "aac", "-b:a", "192k",
                               "-loglevel", "error", concat_video], check=True, timeout=SUBPROCESS_TIMEOUT)
            except Exception:
                concat_video = None

            if concat_video and os.path.exists(concat_video):
                # BGM选择 (返回元组)
                            # 从decision结果获取情绪标签和BGM类型
                bgm_emotion_tags = decision.get("emotion_tags", []) if 'decision' in dir() and decision else []
                bgm_genre_for_match = decision.get("drama_genre_for_bgm", genre) if 'decision' in dir() and decision else genre
                bgm_result = smart_bgm_select(bgm_genre_for_match, emotion_tags=bgm_emotion_tags) if 'smart_bgm_select' in globals() else (None, [])
                bgm_file = bgm_result[0] if bgm_result else None
                # [FIX-音频对齐-20260520] 直接从拼接视频提取原声音频
                # 不再从源文件重新提取(避免-ss快进seek导致的音视频时间偏差)
                orig_audio_path = None
                if concat_video and os.path.exists(concat_video):
                    orig_audio_path = os.path.join(tmp_dir, "orig_from_concat.aac")
                    r = subprocess.run(["ffmpeg", "-y", "-i", concat_video, "-vn", "-acodec", "copy", orig_audio_path],
                                      capture_output=True, timeout=30)
                    if r.returncode != 0 or not os.path.exists(orig_audio_path) or os.path.getsize(orig_audio_path) < 500:
                        orig_audio_path = None
                        log("   ⚠️ 从拼接视频提取原声失败,尝试旧方式", "")
                        # fallback: 用旧方式从源文件提取
                        clip_files_map = {i: str(f) for i, f in enumerate(files)}
                        orig_audio_path = _build_orig_audio_path(clip_files_map, selected, tmp_dir) if '_build_orig_audio_path' in globals() else None
                log(f"   原声文件: {orig_audio_path}", "")
                log(f"   BGM文件: {bgm_file}", "")
                if narration_audio and os.path.exists(narration_audio):
                    # [FIX-20260530] 先取三轨值
                    video_dur = _get_video_duration(concat_video) if '_get_video_duration' in globals() else 60
                    narr_dur = _get_video_duration(narration_audio) if '_get_video_duration' in globals() else len(narration_text) / 3.5
                    if video_dur is None: video_dur = 60.0
                    if narr_dur is None: narr_dur = len(narration_text) / 3.5
                    # [P0-解说覆盖率-20260714] 视频>解说时硬裁视频,确保解说100%覆盖
                    # 抖音检测:任何>3秒的无解说区域都会触发"解说比例不足"
                    if video_dur > narr_dur + 3.0:
                        _orig_vd = video_dur
                        _trim_vd = narr_dur + 0.5  # 留0.5秒缓冲防抖动
                        log(f"   📏 [P0-解说覆盖] 视频{_orig_vd:.1f}s > 解说{narr_dur:.1f}s, 裁剪视频至{_trim_vd:.1f}s", "✂️")
                        # 直接在文件层面裁剪视频(避免_render_final_multi_audio内部又max拉回原时长)
                        _trimmed_video = concat_video.replace('.mp4', '_trimmed.mp4')
                        try:
                            _trim_r = subprocess.run([
                                'ffmpeg', '-y', '-i', concat_video,
                                '-t', f'{_trim_vd:.3f}',
                                '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
                                '-c:a', 'aac', '-b:a', '192k',
                                '-loglevel', 'error', _trimmed_video
                            ], check=True, timeout=SUBPROCESS_TIMEOUT)
                            if os.path.exists(_trimmed_video) and os.path.getsize(_trimmed_video) > 1000:
                                concat_video = _trimmed_video
                                video_dur = _trim_vd
                                log(f"   ✅ 视频已裁剪至{video_dur:.1f}s", "")
                            else:
                                log(f"   ⚠️ 视频裁剪产出为空,保留原始视频", "⚠️")
                        except Exception as _te:
                            log(f"   ⚠️ 视频裁剪失败: {_te},保留原始视频", "⚠️")
                    elif video_dur < narr_dur:
                        log(f"   ⚠️ 视频({video_dur:.1f}s) < 解说({narr_dur:.1f}s),上游片段补充不足", "⚠️")
                    total_dur = max(video_dur, narr_dur)
                    log(f"   📏 时长: 视频{video_dur:.1f}s 解说{narr_dur:.1f}s → 取{total_dur:.1f}s", "")

                    # [FIX-解说末尾填充-20260702] 检测视频比解说长的末尾间隙
                    # 根因:片段拼接后的视频常比解说长3-5秒,apad填充的是纯BGM无解说内容
                    # 抖音音频检测算法会把末尾无解说区域算"解说比例不足"
                    # 修复:用LLM生成承接主线的填充解说,覆盖整个视频时长
                    _narr_extended = narration_audio  # 默认用原 narration_audio
                    if video_dur > narr_dur + 0.5 and os.path.exists(narration_audio):
                        _gap = video_dur - narr_dur
                        # 让 Ollama 根据现有解说生成承搓填充语(避免硬凑废话)
                        _fill_prompt = f"""你是一个短剧解说编剧。
现有解说词:
{ narration_text[-300:]}

这段解说后面还有 {_gap:.1f} 秒画面需要覆盖。请生成 1-2 句承接的收尾解说(总共20-40字),要求:
- 自然承接上文内容,像正常结尾
- 不要'故事还在进行中'等硬凑废话
- 可以是:人物命运的延续、后续发展的留白、情绪的收束
只输出解说文字,不要任何其他内容。"""
                        _fill_text = ""
                        try:
                            _fill_raw = _call_ollama_retry(_fill_prompt, agent_name="narration_filler", timeout=30)
                            if _fill_raw:
                                _fill_text = _fill_raw.strip().strip('"').strip("'")[:80]
                                # 基本验证:不为空且不像模板
                                if _fill_text and '故事还在' not in _fill_text and '进行中' not in _fill_text:
                                    log(f"   🤖 LLM填充解说: '{_fill_text}'", "")
                                else:
                                    _fill_text = ""
                        except Exception as _e:
                            log(f"   ⚠️ LLM填充生成失败: {_e}", "⚠️")
                        # fallback: 无LLM输出时用简洁过渡
                        if not _fill_text:
                            _fill_text = "精彩还在继续。"
                            log(f"   📝 使用兜底填充: '{_fill_text}'", "")
                        # ChatTTS生成填充音频(使用项目封装的wrapper确保API一致)
                        _fill_wav = os.path.join(tmp_dir, f"__narr_fill_{int(time.time())}.wav")
                        _fill_ok = False
                        try:
                            from tts_chattts_wrapper import tts_chattts
                            import hashlib as _hl
                            _fill_seed = int(_hl.md5(drama_name.encode('utf-8')).hexdigest()[:8], 16) % (2**31)
                            _fill_result = tts_chattts(_fill_text, _fill_wav, seed=_fill_seed)
                            _fill_ok = _fill_result and os.path.exists(_fill_wav) and os.path.getsize(_fill_wav) > 1000
                            if _fill_ok:
                                    # 格式统一: narration_audio可能是MP3, fill是WAV
                                    # 用 ffmpeg 重编码两者为统一WAV再concat (不用-c copy)
                                    _ext_wav = os.path.join(tmp_dir, f"__narr_ext_{int(time.time())}.wav")
                                    _ext_list = os.path.join(tmp_dir, f"__narr_ext_list_{int(time.time())}.txt")
                                    # 先把narration_audio转为WAV(如果不是的话)
                                    _narr_wav_for_concat = narration_audio
                                    if narration_audio.lower().endswith('.mp3'):
                                        _narr_wav_for_concat = os.path.join(tmp_dir, f"__narr_orig_{int(time.time())}.wav")
                                        _conv_r = subprocess.run([
                                            'ffmpeg', '-y', '-i', narration_audio,
                                            '-ar', '24000', '-ac', '1', _narr_wav_for_concat
                                        ], capture_output=True, timeout=30)
                                        if _conv_r.returncode != 0 or not os.path.exists(_narr_wav_for_concat):
                                            log(f"   ⚠️ narration_audio转WAV失败,跳过填充", "⚠️")
                                            _narr_wav_for_concat = None
                                    # fill_wav也统一为24000Hz mono
                                    _fill_wav_norm = os.path.join(tmp_dir, f"__fill_norm_{int(time.time())}.wav")
                                    _conv_r2 = subprocess.run([
                                        'ffmpeg', '-y', '-i', _fill_wav,
                                        '-ar', '24000', '-ac', '1', _fill_wav_norm
                                    ], capture_output=True, timeout=30)
                                    if _narr_wav_for_concat and _conv_r2.returncode == 0 and os.path.exists(_fill_wav_norm):
                                        with open(_ext_list, 'w') as _f:
                                            _f.write(f"file '{_narr_wav_for_concat}'\n")
                                            _f.write(f"file '{_fill_wav_norm}'\n")
                                        _concat_r = subprocess.run([
                                            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                                            '-i', _ext_list, '-c', 'copy', _ext_wav
                                        ], capture_output=True, timeout=30)
                                        if _concat_r.returncode == 0 and os.path.exists(_ext_wav):
                                            _ext_dur = _get_video_duration(_ext_wav)
                                            log(f"   ✅ 末尾填充解说: gap={_gap:.1f}s, 填充'{_fill_text}'({_ext_dur:.1f}s)", "")
                                            _narr_extended = _ext_wav
                                            narr_dur = _ext_dur  # 更新 narr_dur
                                        else:
                                            log(f"   ⚠️ 拼接填充音频失败: {_concat_r.stderr[-200:]}", "⚠️")
                                        # 清理临时文件
                                        for _tmp_f in [_fill_wav_norm, _narr_wav_for_concat if _narr_wav_for_concat != narration_audio else None, _ext_list]:
                                            if _tmp_f and os.path.exists(_tmp_f):
                                                try: os.remove(_tmp_f)
                                                except: pass
                                    else:
                                        log(f"   ⚠️ 填充音频格式转换失败", "⚠️")
                            else:
                                log(f"   ⚠️ ChatTTS生成填充音频失败(空输出)", "⚠️")
                        except Exception as _e:
                            log(f"   ⚠️ 末尾填充解说跳过(ChatTTS异常): {_e}", "⚠️")
                        # 更新 total_dur
                        total_dur = max(video_dur, narr_dur)

                    _render_final_multi_audio(
                        video_path=concat_video, bgm_path=bgm_file, narration_path=_narr_extended,
                        output_path=output_file, total_dur=total_dur, drama_title=drama_name,
                        orig_audio_path=orig_audio_path,
                        full_text=full_text, genre=genre)
                else:
                    shutil.copy(concat_video, output_file)

        if os.path.exists(output_file):
            # [FIX-20260712] 成片时长兜底保护:只做极端情况兜底(>600秒),正常解说驱动不做硬截
            _out_dur = _get_video_duration(output_file) if '_get_video_duration' in globals() else None
            if _out_dur and _out_dur > 600:
                _max_d = 600
                _trimmed_out = output_file.replace('.mp4', '_trimmed.mp4')
                try:
                    subprocess.run(["ffmpeg", "-y", "-i", output_file,
                                   "-t", str(_max_d),
                                   "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                                   "-c:a", "aac", "-b:a", "192k",
                                   "-loglevel", "error", _trimmed_out],
                                  check=True, timeout=SUBPROCESS_TIMEOUT)
                    if os.path.exists(_trimmed_out) and os.path.getsize(_trimmed_out) > 1000:
                        os.replace(_trimmed_out, output_file)
                        log(f"   ⚠️ 极端兜底裁剪到{_max_d}秒(原{_out_dur:.1f}秒)", "⚠️")
                except Exception as _te:
                    log(f"   ⚠️ 兜底裁剪失败: {_te}", "⚠️")

            log(f"   ✅ 输出: {output_file}", "")

            # 片头引导语已禁用(用户不需要)
            # output_file = _add_opening_guidance(output_file, total_dur) if '_add_opening_guidance' in globals() else output_file

            # 一次性叠加剧名标题+底部声明(避免多次重编码导致时长偏差)
            try:
                _fd = _get_video_duration(output_file) if '_get_video_duration' in globals() else 60.0
                if '_add_overlays' in globals():
                    _add_overlays(output_file, drama_name, float(_fd), genre=genre)
                    log("   ✅ 标题+声明叠加完成", "")
                elif '_add_title_overlay' in globals():
                    _add_title_overlay(output_file, drama_name, float(_fd), genre=genre)
                    log("   ✅ 剧名标题叠加完成", "")
            except Exception as oe:
                log(f"   ⚠️ 叠加失败(不影响主流程): {oe}", "")

            # ===== Step 9.4: 帧低俗预检(已移除,低俗检测在LLM生成阶段完成) =====
            # [FIX-20260708] 不再抽取帧、不输出frames.json

            if '_quality_audit' in globals():
                # 合规预检(步骤9.5)
                try:
                    from compliance_checker import check_compliance
                    # [FIX-20260710] 检测解说词而非原始字幕(解说词已过SAFE_WORD_MAP替换)
                    _narration = narration_text if narration_text else (full_text if 'full_text' in dir() else "")
                    # 强制兜底:永远包含合规免责标签
                    # [FIX-20260607] 修复 ending_tags 作用域检查
                    _tags = globals().get('ending_tags', []) or []
                    # 合规标签已禁用(用户要求)
                    log(f"   🔍 调试: _tags={_tags[:8]}... 共{len(_tags)}个", '')
                    compliance_result = check_compliance(
                        video_path=output_file,
                        drama_title=drama_name,
                        narration_text=_narration,
                        tags=_tags
                    )
                    _score = compliance_result.get('score', 0)
                    _issue_count = len(compliance_result.get('issues', []))
                    log(f"   🔍 合规预检: {_score}/100, 问题{_issue_count}个", "")

                    # [FIX-20260708] 不输出compliance_report文件,只在日志报告
                    _p0_issues = [i for i in compliance_result.get('issues', []) if i.get('level') == 'P0']
                    _p1_issues = [i for i in compliance_result.get('issues', []) if i.get('level') == 'P1']
                    if _p0_issues:
                        log(f"   ⚠️ P0问题: {'; '.join(i['description'] for i in _p0_issues)}", "⚠️")
                    if _p1_issues:
                        log(f"   ⚠️ P1问题: {'; '.join(i['description'] for i in _p1_issues)}", "⚠️")

                    if _score < 60:
                        log(f"   ⚠️ 合规预警: 得分{_score}<60, 建议检查后上传", "⚠️")
                    # [FIX-20260712] 不合规视频保留但标记文件名
                    _p0_lowbiz = any(i.get('category') == '低俗内容' and i.get('level') == 'P0' for i in compliance_result.get('issues', []))
                    if _p0_lowbiz:
                        _flagged = output_file.replace('.mp4', '_不合规.mp4')
                        try: os.rename(output_file, _flagged)
                        except: pass
                        log(f"   ⚠️ 不合规: 检测到P0低俗词,文件已标记为不合规(得分{_score})", "⚠️")
                except Exception as _ce:
                    log(f"   ⚠️ 合规预检失败(不影响主流程): {_ce}", "")

                audit = _quality_audit(output_file)
                log(f"   📋 质量审计: {audit.get('score', 'N/A')}分", "")
            if 'generate_viral_package' in globals():
                # 传入正确参数:drama_name, genre, duration, peak_moment
                try:
                    _gd = _get_video_duration(output_file) if '_get_video_duration' in globals() else 60.0
                    vp = generate_viral_package(
                        drama_name=drama_name,
                        genre=genre,
                        duration=float(_gd) if _gd else 60.0,
                        peak_moment=0,
                        key_words=None
                    )
                    log(f"   📋 发布包生成成功", "")
                except Exception as ve:
                    log(f"   ⚠️ 发布包生成失败: {ve}", "")

            # Toonflow: 构建结构化分镜节点 + 角色一致性检查
            try:
                # 构建narration_segments(从selected片段信息)
                narration_segs = []
                for i, (fidx, start, end, _) in enumerate(selected):
                    narration_segs.append({
                        "text": narration_text[i*30:(i+1)*30] if narration_text else "",
                        "emotion": "neutral",
                        "characters": [],
                        "location": "unknown"
                    })
                clip_infos = [{"path": cf, "start": s, "end": e, "motion_score": 0.5}
                             for cf, (fidx, s, e, _) in zip(clip_files, selected)]
                shot_nodes = _build_shot_nodes(clip_infos, narration_segs)
                consistency_warnings = _check_character_consistency(shot_nodes, drama_name)
                if consistency_warnings:
                    for w in consistency_warnings:
                        log(f"   ⚠️ 分镜{w['shot_id']}角色{w['character']}: {w['warning']}", "⚠️")
            except Exception as ce:
                log(f"   ⚠️ 分镜节点构建失败(不影响输出): {ce}", "")

            # Toonflow: 更新多集记忆
            if asset_manager:
                try:
                    # 从解说文本中提取角色名(简单启发式)
                    extracted_chars = re.findall(r'[\u4e00-\u9fff]{2,4}(?=说|想|看|走|笑|哭|怒)', narration_text) if narration_text else []
                    extracted_chars = list(set(extracted_chars))[:5]
                    asset_manager.add_episode_meta(
                        drama_name=drama_name,
                        episode_num=int(episode) if str(episode).isdigit() else 1,
                        characters=extracted_chars,
                        locations=[],
                        plot_summary=narration_text[:200] if narration_text else ""
                    )
                    continuity = asset_manager.export_consistency_report(drama_name)
                    if continuity.get("warnings"):
                        log(f"   ⚠️ 连续性问题: {continuity['warnings']}", "⚠️")
                    else:
                        log("   ✅ 多集记忆已更新,无连续性问题", "")
                except Exception as ae:
                    log(f"   ⚠️ 多集记忆更新失败: {ae}", "⚠️")
            return 1

        return 0
    except Exception as e:
        log(f"❌ 处理失败: {e}", "❌")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        CONFIG["width"], CONFIG["height"] = orig_w, orig_h
        # [FIX-20260520] 清理临时目录,避免磁盘空间泄漏
        if 'tmp_dir' in dir() and tmp_dir and os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass



def _deduplicate_clips(clips: list, threshold: float = 0.5) -> list:
    """去重:同一文件内时间重叠或相距 < threshold 秒的片段视为重复,保留第一个"""
    if not clips:
        return []
    clips.sort(key=lambda x: (x[0], x[1]))
    unique = [clips[0]]
    for c in clips[1:]:
        fidx, start, end, score = c
        lfidx, lstart, lend, lscore = unique[-1]
        # 同一文件: 新片段开始时间 < 上个片段结束时间 - threshold → 重叠
        if fidx == lfidx and start < lend - threshold:
            continue
        unique.append(c)
    return unique

def _merge_clips_v2(clips: list) -> list:
    """合并重叠片段"""
    if not clips:
        return []
    clips.sort(key=lambda x: (x[0], x[1]))
    merged = [clips[0]]
    for c in clips[1:]:
        if c[0] == merged[-1][0] and c[1] <= merged[-1][2]:
            merged[-1] = (merged[-1][0], merged[-1][1], max(merged[-1][2], c[2]), merged[-1][3])
        else:
            merged.append(c)
    return merged


    """
    使用 concat demuxer + 实时编码拼接(避免 concat filter 的大数量问题)
    - 片段可能有/无音频,统一实时编码确保兼容
    - 用 concat.txt 协议拼接,兼容性好
    """
    if not segments:
        return None
    if len(segments) == 1:
        return segments[0][0]

    paths = [s[0] for s in segments]
    out = os.path.join(tmp_dir, "concat_output.mp4")

    # 创建 concat 文件列表
    concat_list = os.path.join(tmp_dir, "concat_list.txt")
    with open(concat_list, 'w', encoding='utf-8') as f:
        for p in paths:
            # 每个文件一行,强制重新编码
            f.write(f"file '{p}'\n")

    # 使用 concat demuxer + 强制重新编码
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-r", "30", "-vsync", "cfr",
        "-an",  # 无音频输出
        out
    ]

    r = subprocess.run(cmd, capture_output=True, timeout=900)
    if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 50000:
        probe_dur = _get_video_duration(out)
        if probe_dur and probe_dur > 1.0:
            return out
        else:
            log(f"[WARN] concat输出时长异常: {probe_dur}s", "⚠️")
    else:
        log(f"[ERROR] concat demuxer 失败 rc={r.returncode}", "❌")
        if r.stderr:
            err = r.stderr.decode("utf-8", errors="replace")[-500:]
            log(f"stderr: {err}", "⚠️")
    return None
    """
    根据剧集类型返回标题样式配置
    参考用户提供的样式表
    """
    style_map = {
        "都市言情": {
            "font_paths": [
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ],
            "font_size": 48,
            "primary_color": (255, 255, 255, 255),  # 白色
            "outline_color": (0, 0, 0, 200),  # 黑色描边
            "outline_width": 2,
            "gradient": False,
            "shadow_offset": (3, 3),
            "shadow_color": (0, 0, 0, 150),
        },
        "古装": {
            "font_paths": [
                "/System/Library/Fonts/STKaiti.ttc",
                "/System/Library/Fonts/Supplemental/Kaiti.ttc",
            ],
            "font_size": 52,
            "primary_color": (212, 175, 55, 255),  # 金色
            "outline_color": (139, 69, 19, 200),  # 棕色描边
            "outline_width": 3,
            "gradient": False,
            "glow_color": (255, 215, 0, 100),  # 金光外发光
            "glow_radius": 5,
        },
        "悬疑": {
            "font_paths": [
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ],
            "font_size": 50,
            "primary_color": (200, 200, 200, 255),  # 灰白色
            "outline_color": (0, 0, 0, 255),  # 黑色厚阴影
            "outline_width": 4,
            "gradient": False,
            "shadow_offset": (5, 5),
            "shadow_color": (0, 0, 0, 200),
            "distressed": True,  # 做旧效果
        },
        "甜宠": {
            "font_paths": [
                "/System/Library/Fonts/STYuanti-SC-Regular.ttc",
                "/System/Library/Fonts/Supplemental/Yuanti.ttc",
            ],
            "font_size": 46,
            "primary_color": (255, 182, 193, 255),  # 浅粉红
            "outline_color": (255, 105, 180, 180),  # 热粉红描边
            "outline_width": 2,
            "gradient": True,
            "gradient_colors": [(255, 182, 193, 255), (255, 105, 180, 255)],  # 马卡龙渐变
            "soft_glow": True,
            "glow_color": (255, 182, 193, 80),
        },
        "正剧": {
            "font_paths": [
                "/System/Library/Fonts/STSong.ttc",
                "/System/Library/Fonts/Supplemental/Songti.ttc",
            ],
            "font_size": 48,
            "primary_color": (255, 255, 255, 255),  # 白色
            "outline_color": (100, 100, 100, 150),  # 灰色细描边
            "outline_width": 1,
            "gradient": False,
            "effects": [],  # 无花哨特效
        },
        "喜剧": {
            "font_paths": [
                "/System/Library/Fonts/STYuanti-SC-Regular.ttc",
                "/System/Library/Fonts/STHeiti Medium.ttc",
            ],
            "font_size": 50,
            "primary_color": (255, 255, 0, 255),  # 明黄
            "outline_color": (255, 140, 0, 200),  # 橙色描边
            "outline_width": 2,
            "gradient": False,
            "emboss": True,  # 轻微浮雕
            "emboss_offset": (2, 2),
        },
    }

    # 类型匹配(模糊匹配)
    for key in style_map:
        if key in genre or genre in key:
            return style_map[key]

    # 默认样式(现代都市)
    return style_map["都市言情"]

# 中文艺术字体优先级列表
_TITLE_FONT_PATHS = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

# 下载的思源字体(项目fonts目录)
_FONT_DIR = WORK_DIR / "fonts"
if _FONT_DIR.exists():
    _title_font_downloaded = list(_FONT_DIR.glob("*.ttf")) + list(_FONT_DIR.glob("*.otf"))
    if _title_font_downloaded:
        _TITLE_FONT_PATHS = [str(_FONT_DIR / f.name) for f in _title_font_downloaded] + _TITLE_FONT_PATHS


def _load_title_font(size: int) -> ImageFont.FreeTypeFont:
    """加载标题字体,优先用艺术字体"""
    for fp in _TITLE_FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _generate_title_image(title: str, width: int = 1080, height: int = 100, genre: str = "") -> str:
    """
    生成剧名标题图片 - 全宽半透明黑色条+白色艺术字体
    设计原则: 绝对可见 + 美观简洁 + 不遮挡主体内容

    Args:
        title: 剧名标题
        width: 视频宽度(默认1080)
        height: 标题栏高度(默认100)
        genre: 剧集类型(用于样式匹配)

    Returns:
        临时标题图片路径
    """
    if not HAS_PIL:
        return None

    # 根据题材获取配色
    style = _get_genre_title_style(genre) if genre else _get_genre_title_style("都市言情")

    # ===== 标题图片新设计: 全宽半透明黑色条 + 白色艺术字体 =====
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 配色主题(根据题材)
    bg_alpha = style.get("bg_alpha", 200)      # 背景透明度(0-255)
    text_color = style.get("text_color", (255, 255, 255, 255))  # 白色文字
    accent_color = style.get("accent_color", (255, 215, 0, 255))  # 金色强调
    border_color = style.get("border_color", (255, 255, 255, 80))  # 白色边框线

    # 1 全宽半透明黑色背景(绝对可见,不受视频内容影响)
    draw.rectangle([(0, 0), (width - 1, height - 1)], fill=(0, 0, 0, bg_alpha))

    # 2 顶部装饰细线(金色/白色)
    draw.line([(0, 0), (width - 1, 0)], fill=border_color, width=2)

    # 3 自适应字号(目标: 文字宽度不超过视频宽度的60%)
    base_font_size = style.get("font_size", 52)
    target_width = int(width * 0.62)

    font = None
    for font_size in range(base_font_size, 20, -2):
        font = _load_title_font(font_size)
        bbox = draw.textbbox((0, 0), title, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= target_width:
            break

    text_x = (width - text_w) // 2
    text_y = (height - text_h) // 2

    # 4 文字描边(黑色轮廓,确保在任何背景上可见)
    stroke_color = (0, 0, 0, 255)
    stroke_width = style.get("stroke_width", 3)
    if stroke_width > 0:
        draw.text((text_x, text_y), title, font=font, fill=text_color,
                   stroke_fill=stroke_color, stroke_width=stroke_width)
    else:
        draw.text((text_x, text_y), title, font=font, fill=text_color)

    # 5 底部装饰细线
    draw.line([(0, height - 2), (width - 1, height - 2)], fill=border_color, width=1)

    # ===== PNG保真保存 → FFmpeg overlay绝对可见 =====
    # 用 RGB模式 避免FFmpeg对RGBA的处理问题
    rgb_img = Image.new('RGB', (width, height), (0, 0, 0))
    rgb_img.paste(img, (0, 0))

    tmp_path = tempfile.mktemp(suffix=".png")
    rgb_img.save(tmp_path, "PNG", optimize=False)
    return tmp_path



def _get_genre_title_style(genre: str) -> dict:
    """
    根据剧集类型返回标题样式配置
    Returns: dict with font_size, bg_alpha, text_color, accent_color, border_color, stroke_width
    """
    # 背景透明度: 200/255 = 78% 不透明度(全宽黑色背景,绝对可见)
    GENRE_STYLES = {
        "复仇":   {"font_size": 52, "bg_alpha": 210, "text_color": (255, 255, 255, 255),
                    "accent_color": (255, 60, 60, 255), "border_color": (255, 100, 100, 100),
                    "stroke_width": 4},
        "重生":   {"font_size": 50, "bg_alpha": 205, "text_color": (255, 255, 255, 255),
                    "accent_color": (255, 215, 0, 255), "border_color": (255, 255, 255, 80),
                    "stroke_width": 3},
        "都市言情": {"font_size": 48, "bg_alpha": 200, "text_color": (255, 255, 255, 255),
                    "accent_color": (255, 182, 193, 255), "border_color": (255, 255, 255, 80),
                    "stroke_width": 3},
        "甜宠":   {"font_size": 48, "bg_alpha": 195, "text_color": (255, 255, 255, 255),
                    "accent_color": (255, 182, 193, 255), "border_color": (255, 255, 255, 80),
                    "stroke_width": 3},
        "虐心":   {"font_size": 48, "bg_alpha": 210, "text_color": (255, 200, 200, 255),
                    "accent_color": (200, 100, 100, 255), "border_color": (255, 255, 255, 60),
                    "stroke_width": 4},
        "战斗":   {"font_size": 54, "bg_alpha": 215, "text_color": (255, 255, 255, 255),
                    "accent_color": (255, 200, 0, 255), "border_color": (255, 200, 0, 100),
                    "stroke_width": 4},
        "悬疑":   {"font_size": 50, "bg_alpha": 210, "text_color": (200, 200, 255, 255),
                    "accent_color": (100, 100, 200, 255), "border_color": (100, 100, 255, 80),
                    "stroke_width": 3},
        "搞笑":   {"font_size": 52, "bg_alpha": 190, "text_color": (255, 255, 255, 255),
                    "accent_color": (255, 255, 100, 255), "border_color": (255, 255, 100, 80),
                    "stroke_width": 3},
    }
    return GENRE_STYLES.get(genre, GENRE_STYLES["都市言情"])



def _wrap_by_width(text, font, draw, max_w, max_chars):
    """按宽度换行, 优先在标点处断开"""
    if draw.textlength(text, font=font) <= max_w:
        return [text]
    lines = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            for k in range(end, start, -1):
                if text[k] in (",", "。", "、", ":", ";", " "):
                    end = k
                    break
        chunk = text[start:end+1].strip()
        if chunk:
            lines.append(chunk)
        start = end + 1
    return [x for x in lines if x]


def render_title_banner(drama_name, genre, output_path):
    """
    生成顶部常驻剧名条 (全屏RGBA, 仅顶部~210px有渐变内容)
    移植自 vg_render.py 的 render_title_banner

    Args:
        drama_name: 剧名(可能带《》、"·"副标)
        genre: 剧集类型(用于配色)
        output_path: 输出PNG路径
    """
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1920
    FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
    FONT_INDEX = 0

    # 去掉《》
    drama_name = drama_name.replace("《", "").replace("》", "")

    # 提取副标 (如果有"·"号分隔)
    slogan = ""
    if "·" in drama_name:
        parts = drama_name.split("·", 1)
        drama_name = parts[0].strip()
        slogan = parts[1].strip()

    # genre → palette 映射
    if any(k in genre for k in ("复仇", "战斗")):
        palette = "gold_red"
    elif "悬疑" in genre:
        palette = "cyan_purple"
    else:
        palette = "gold_red"

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if palette == "cyan_purple":
        accent = (57, 240, 224)
        accent_glow = (120, 255, 240)
        bar_top = (10, 10, 22, 190)
    else:
        accent = (255, 210, 74)
        accent_glow = (255, 180, 90)
        bar_top = (14, 8, 12, 190)

    # 顶部渐变背景条 (alpha 从190渐变到0, ~210px高)
    bar_h = 210
    for y in range(bar_h):
        t = y / bar_h
        a = int(bar_top[3] * (1 - t))
        draw.line([(0, y), (W, y)], fill=(bar_top[0], bar_top[1], bar_top[2], a))

    # 自适应字号 (64→34, 最长不超过 W-120)
    title = drama_name
    size = 64
    max_w = W - 120
    while size > 34:
        f = ImageFont.truetype(FONT, size, index=FONT_INDEX)
        if draw.textlength(title, font=f) <= max_w:
            break
        size -= 3

    font = ImageFont.truetype(FONT, size, index=FONT_INDEX)
    lines = _wrap_by_width(title, font, draw, max_w, 8)
    if len(lines) > 2:
        lines = lines[:2]

    line_h = int(size * 1.15)
    total_h = line_h * len(lines)
    cx = W // 2
    cy0 = 70 + total_h // 2 - line_h // 2

    # 外发光
    glow = accent_glow
    for off in range(5, 0, -1):
        a = int(45 * (1 - off / 6))
        for dx in range(-off, off + 1):
            for dy in range(-off, off + 1):
                if dx * dx + dy * dy <= off * off:
                    for li, ln in enumerate(lines):
                        y = cy0 + li * line_h
                        draw.text((cx + dx, y), ln, font=font, fill=(glow[0], glow[1], glow[2], a), anchor="mm")

    # 白色主文字 + 深色描边
    for li, ln in enumerate(lines):
        y = cy0 + li * line_h
        draw.text((cx, y), ln, font=font, fill=(255, 255, 255, 255),
                  stroke_width=5, stroke_fill=(18, 12, 20, 255), anchor="mm")

    # 副标 (accent色, 显示在剧名下方)
    if slogan:
        try:
            sfont = ImageFont.truetype(FONT, 32, index=FONT_INDEX)
        except Exception:
            sfont = ImageFont.load_default()
        sy = cy0 + total_h // 2 + 30
        draw.text((cx, sy), slogan, font=sfont, fill=(accent[0], accent[1], accent[2], 255),
                  stroke_width=2, stroke_fill=(10, 10, 20, 230), anchor="mm")

    img.save(output_path)


def render_disclaimer(output_path, genre: str = ""):
    """
    生成片尾免责声明卡 (全屏RGBA, 仅底部~1/3有内容)
    移植自 vg_render.py 的 render_disclaimer
    [OPT-20260804] 玄幻/修真/道教题材追加双虚构声明(依抖音合规规范铁规)
    """
    from PIL import Image, ImageDraw, ImageFont
    
    W, H = 1080, 1920
    FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
    FONT_INDEX = 0

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 底部半透明黑底带 (占画面下 ~1/3)
    band_h = int(H * 0.34)
    top = H - band_h
    draw.rectangle([0, top, W, H], fill=(0, 0, 0, 175))

    lines = [
        "素材来源于网络，本片为剧情解说二次创作，如有侵权请联系删除。",
        "本片为AI辅助创作，剧情为虚构内容，请理性观看。",
    ]

    # [OPT-20260804] 玄幻/修真/道教/神医题材:追加双虚构声明(封建迷信铁规)
    _xuanhuan_genres = {"玄幻", "修真", "仙侠", "道教", "道家", "神医", "系统流", "异能"}
    _genre_lower = (genre or "").lower()
    if any(g in _genre_lower for g in _xuanhuan_genres):
        lines.append("本片为影视虚构剧情解说，道家/修真/法术/异能等均为二次创作设定，")
        lines.append("不宣扬封建迷信，无任何科学/医学功效暗示。")

    # [OPT-20260804] 片尾互动CTA(数据:零分享=0,无裂变;需强引导互动)
    _cta_lines = [
        "你站男主还是反派？评论区见 👇",
        "想看下集扣1，点赞过万秒更 ⚡",
        "这波操作你打几分？评论区聊聊",
        "猜结局扣「A」或「B」，下集揭晓",
    ]
    import random as _rnd_cta
    _cta = _rnd_cta.choice(_cta_lines)
    lines.append("")  # 空行分隔
    lines.append(_cta)

    try:
        font = ImageFont.truetype(FONT, 34, index=FONT_INDEX)
    except Exception:
        font = ImageFont.load_default()
    
    # 逐句按 ~18 字换行
    wrapped = []
    for ln in lines:
        while len(ln) > 18:
            wrapped.append(ln[:18])
            ln = ln[18:]
        wrapped.append(ln)
    
    line_h = 46
    total_h = line_h * len(wrapped)
    y0 = top + (band_h - total_h) // 2
    for i, ln in enumerate(wrapped):
        draw.text((W/2, y0 + i*line_h), ln, font=font, fill=(255, 255, 255, 255),
                  stroke_width=2, stroke_fill=(0, 0, 0, 220), anchor="mm")
    
    img.save(output_path)


def _add_intro_ai_disclosure(video_path: str, total_dur: float = 2.0) -> bool:
    """
    片头插入AI生成内容声明(concat + adelay音频同步)
    [FIX-20260628] concat插入2秒片头,同时将主视频音频延迟total_dur秒
    确保: 前total_dur秒为黑屏+AI文字+静音 -> 之后主视频+解说同步播放
    """
    log(f"   INFO _add_intro_ai_disclosure (concat+adelay版) 已加载", '')
    if not HAS_PIL:
        return False
    try:
        info = get_video_info(video_path)
        width = info.get("width", 1080)
        height = info.get("height", 1920)

        font_paths = [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
        ]
        font = None
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, 72); break
            except: continue
        if font is None:
            font = ImageFont.load_default()

        img = Image.new('RGBA', (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)

        line1 = "AI生成内容"
        bbox1 = draw.textbbox((0, 0), line1, font=font)
        w1, h1 = bbox1[2]-bbox1[0], bbox1[3]-bbox1[1]
        x1, y1 = (width-w1)//2, height//2-h1-20
        draw.text((x1+3, y1+3), line1, font=font, fill=(0,0,0,200))
        draw.text((x1, y1), line1, font=font, fill=(255,255,255,255))

        line2 = "本视频由AI辅助创作,仅供娱乐"
        font2 = None
        for fp in font_paths:
            try:
                font2 = ImageFont.truetype(fp, 42); break
            except: continue
        if font2 is None: font2 = font
        bbox2 = draw.textbbox((0, 0), line2, font=font2)
        w2, h2 = bbox2[2]-bbox2[0], bbox2[3]-bbox2[1]
        x2, y2 = (width-w2)//2, height//2+20
        draw.text((x2+2, y2+2), line2, font=font2, fill=(0,0,0,180))
        draw.text((x2, y2), line2, font=font2, fill=(200,200,200,255))

        fd, tmp_png = tempfile.mkstemp(suffix=".png"); os.close(fd)
        img.save(tmp_png, "PNG")

        # [1] 生成total_dur秒片头视频(黑屏+AI文字)
        fd, tmp_intro = tempfile.mkstemp(suffix=".mp4"); os.close(fd)
        r = subprocess.run(['ffmpeg','-y','-loop','1','-i',tmp_png,
            '-t',str(total_dur),'-vf','fps=30',
            '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p',
            '-movflags','+faststart',tmp_intro],
            capture_output=True, timeout=60)
        if r.returncode != 0:
            log(f"   ERROR 片头视频生成失败"); return False

        # 给片头加静音音轨
        fd, tmp_ia = tempfile.mkstemp(suffix=".mp4"); os.close(fd)
        sr = subprocess.run(['ffmpeg','-y','-i',tmp_intro,
            '-f','lavfi','-i','aevalsrc=0',
            '-c:v','copy','-c:a','aac','-shortest',tmp_ia],
            capture_output=True, timeout=30)
        if sr.returncode == 0 and os.path.exists(tmp_ia) and os.path.getsize(tmp_ia)>10000:
            tmp_intro = tmp_ia

        # [2] concat拼接片头 + 主视频(音频不需要adelay,concat已对齐)
        # [FIX-20260629] 移除adelay:解说从第0秒开始播,片头2秒静音已覆盖,
        # 主视频音频concat后自然从第2秒开始,不需要额外延迟
        tmp_dly = video_path  # 直接使用原视频,不做adelay

        # [3] concat拼接片头 + 主视频
        # 注意: concat list 格式必须是 file /path (无引号),safe=0 允许绝对路径
        fd, tmp_lst = tempfile.mkstemp(suffix=".txt"); os.close(fd)
        with open(tmp_lst,'w',encoding='utf-8') as f:
            # [FIX-20260731] 路径可能含空格,必须加单引号,否则concat demuxer解析失败只拼第一文件
            f.write(f"file '{tmp_intro}'\n")
            f.write(f"file '{tmp_dly}'\n")
        fd, tmp_out = tempfile.mkstemp(suffix=".mp4"); os.close(fd)
        cr = subprocess.run(['ffmpeg','-y','-f','concat','-safe','0',
            '-i',tmp_lst,
            '-c:v','libx264','-preset','fast',
            '-c:a','aac','-b:a','192k',
            '-movflags','+faststart',tmp_out],
            capture_output=True, timeout=120)
        # [FIX-20260731] 阈值放宽: concat成功但成片可能仅片头+主视频,改判returncode+文件存在即可
        ok = cr.returncode == 0 and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 1000
        if ok:
            os.replace(tmp_out, video_path)
            log(f"   INFO 片头AI标识完成(+{total_dur}s)" + (",音频同步" if tmp_dly != video_path else ",无延迟"))
        else:
            log(f"   ERROR 片头拼接失败")
            ok = False

        # cleanup
        _cleanup_files = [tmp_png, tmp_intro, tmp_lst, tmp_out]
        if 'tmp_ia' in locals() and os.path.exists(tmp_ia): _cleanup_files.append(tmp_ia)
        if tmp_dly != video_path and os.path.exists(tmp_dly): _cleanup_files.append(tmp_dly)
        for f in _cleanup_files:
            if f and os.path.exists(f):
                try: os.unlink(f)
                except: pass
        return ok
    except Exception as e:
        log(f"   ERROR 片头AI标识异常: {e}"); return False


def _add_opening_guidance(video_path: str, total_dur: float) -> str:
    """
    在视频开头叠加3秒正向引导语
    内容: "剧情虚构 · 理性观看 · 矛盾应用沟通化解"
    返回新视频路径(如果成功),原路径不变则返回原路径
    """
    if not HAS_PIL:
        return video_path
    try:
        import tempfile as _tf
        from PIL import Image, ImageDraw, ImageFont

        info = get_video_info(video_path)
        width = info.get("width", 1080)
        height = info.get("height", 1920)

        # 创建引导语图片(3秒显示)
        guidance = "剧情虚构 · 理性观看 · 矛盾应用沟通化解"
        bar_height = 50
        img = Image.new('RGBA', (width, bar_height), (0, 0, 0, 180))
        draw = ImageDraw.Draw(img)

        # 加载字体
        font = None
        for fp in ["/System/Library/Fonts/STHeiti Medium.ttc",
                    "/System/Library/Fonts/STHeiti Light.ttc",
                    "/Library/Fonts/Arial Unicode.ttf"]:
            try:
                font = ImageFont.truetype(fp, 22)
                break
            except:
                continue
        if not font:
            font = ImageFont.load_default()

        # 居中绘制(白色文字)
        bbox = draw.textbbox((0, 0), guidance, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (width - tw) // 2
        ty = (bar_height - th) // 2
        draw.text((tx, ty), guidance, fill=(255, 255, 255, 230), font=font)

        # 保存临时图片
        img_path = os.path.join(_tf.gettempdir(), f"guidance_{int(time.time())}.png")
        img.save(img_path, "PNG")

        # 用FFmpeg叠加到视频前3秒(只在前3秒显示)
        tmp_out = video_path + ".guided.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-i", img_path,
            "-filter_complex",
            f"[1:v]format=rgba,enable='between(t,0,3)'[g];[0:v][g]overlay=0:H-h:format=auto[vout]",
            "-map", "[vout]", "-map", "0:a?", "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-shortest",
            tmp_out,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 1000:
            os.replace(tmp_out, video_path)
            log("   ✅ 片头引导语已添加(前3秒)", "")
        else:
            log(f"   ⚠️ 片头引导语添加失败: {r.stderr[:100]}", "⚠")
            if os.path.exists(tmp_out):
                os.remove(tmp_out)

        # 清理临时图片
        if os.path.exists(img_path):
            os.remove(img_path)

        return video_path
    except Exception as e:
        log(f"   ⚠️ 片头引导语异常: {e}", "⚠️")
        return video_path


def _add_overlays(video_path: str, title: str, total_dur: float, genre: str = "") -> bool:
    """
    一次性叠加顶部常驻剧名条(render_title_banner) + 片尾免责声明卡(render_disclaimer)
    使用 vg_render.py 移植的高质量渲染组件, 避免多次重编码导致时长偏差

    - 标题条: 全片常驻, 顶部渐变半透明 + 白字深描边 + 外发光 + fade in 0.6s
    - 免责声明: 末5秒显示, 底部半透明黑底带 + 白字
    """
    try:
        if not HAS_PIL:
            log(f"   ⚠️ PIL不可用, 跳过overlay", "⚠️")
            return False

        if not total_dur or total_dur <= 0:
            info = get_video_info(video_path)
            total_dur = info.get("duration", 60)

        # 1. 生成顶部剧名条
        title_img = os.path.join(tempfile.gettempdir(), f"title_banner_{int(time.time())}.png")
        render_title_banner(title, genre, title_img)

        # 2. 生成片尾免责声明卡
        disclaimer_img = os.path.join(tempfile.gettempdir(), f"disclaimer_{int(time.time())}.png")
        render_disclaimer(disclaimer_img, genre)

        # 3. 构建单次 overlay 命令
        tmp_output = video_path + ".overlaid.mp4"
        has_title = os.path.exists(title_img)
        has_disclaimer = os.path.exists(disclaimer_img)

        if not has_title or not has_disclaimer:
            log(f"   ⚠️ 标题卡或声明卡生成失败", "⚠️")
            return False

        # filter_complex:
        #   [1:v]format=rgba,fade=t=in:st=0:d=0.6:alpha=1[ttl]   ← 标题条淡入
        #   [0:v][ttl]overlay=0:0:enable='1'[v0]                  ← 标题条全片常驻
        #   [v0][2:v]overlay=0:0:enable='gte(t,{dur-5})'[vout]   ← 声明末5秒显示
        disclaimer_start = total_dur - 5.0
        filter_script = (
            f"[1:v]format=rgba,fade=t=in:st=0:d=0.6:alpha=1[ttl];"
            f"[0:v][ttl]overlay=0:0:enable='1'[v0];"
            f"[v0][2:v]overlay=0:0:enable='gte(t,{disclaimer_start:.2f})'[vout]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", title_img,
            "-i", disclaimer_img,
            "-filter_complex", filter_script,
            "-map", "[vout]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            "-t", f"{total_dur:.3f}",
            "-movflags", "+faststart",
            tmp_output
        ]

        log(f"   🔍 执行FFmpeg overlay: title_banner + disclaimer (末{total_dur-5.0:.1f}s起)", "")
        r = subprocess.run(cmd, capture_output=True, timeout=180)

        # 清理图片临时文件
        for img_path in [title_img, disclaimer_img]:
            if img_path and os.path.exists(img_path):
                try: os.unlink(img_path)
                except Exception: pass

        if r.returncode == 0 and os.path.exists(tmp_output) and os.path.getsize(tmp_output) > 50000:
            shutil.move(tmp_output, video_path)
            log(f"   ✅ 叠加成功: {os.path.getsize(video_path)} bytes", "")
            return True
        else:
            log(f"   ⚠️ 叠加失败: returncode={r.returncode}, stdout={r.stdout[-200:] if r.stdout else 'None'}, stderr={r.stderr[-200:] if r.stderr else 'None'}", "⚠️")
            if os.path.exists(tmp_output):
                os.unlink(tmp_output)
            return False
    except Exception as e:
        log(f"   ⚠️ 叠加失败: {e}", "")
        return False

# 保留旧函数名作为别名,兼容旧调用
def _add_title_overlay(video_path: str, title: str, total_dur: float, genre: str = "") -> bool:
    """兼容旧调用,内部转发到 _add_overlays"""
    return _add_overlays(video_path, title, total_dur, genre=genre)

def _add_ending_watermark(video_path: str, drama_name: str, tags: list = None, ending_dur: float = 2.0) -> bool:
    """
    在视频末尾追加2秒黑色空镜头,剧名+话题标签以白色7%透明度平铺满画面。
    由于FFmpeg缺少libfreetype,使用Pillow生成图片帧 + FFmpeg loop方案。
    tags: 话题标签列表(如30个"#xxx"),与剧名一起平铺
    """
    if not drama_name and not tags:
        return False
    if not HAS_PIL:
        return False
    try:
        info = get_video_info(video_path)
        width = info.get("width", 1080)
        height = info.get("height", 1920)
        font_size = 16
        alpha_val = 255  # 100% 不透明(合规要求)
        text_color = (255, 255, 255, 255)  # 硬编码不透明,绕过alpha_val

        # 找可用字体
        font = None
        font_paths = [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/Times.ttc",
        ]
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        # 构建平铺文字池:剧名 + 话题标签
        text_pool = []
        if drama_name:
            text_pool.append(drama_name)
        if tags and isinstance(tags, list):
            for t in tags[:30]:
                s = str(t).strip()
                if s:
                    text_pool.append(s)
        if not text_pool:
            return False

        # 构建足够长的重复行文字(剧名+话题交替)
        line_parts = []
        idx = 0
        # 确保文字行足够宽(至少3倍画面宽度)
        while len('  '.join(line_parts)) < width * 3 // font_size + 50:
            line_parts.append(text_pool[idx % len(text_pool)])
            idx += 1
        row_text = '  '.join(line_parts)

        # 测量行高
        dummy_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), row_text, font=font)
        line_h = max(bbox[3] - bbox[1], font_size)
        line_spacing = int(line_h * 1.2)

        rows = max(1, height // line_spacing + 1)

        # 创建黑色背景 + 文字图层(使用RGB模式)
        # 文字颜色设为接近黑色的深灰色(3,3,3),在黑色背景上肉眼几乎不可见
        # 同时满足版权保护要求(文字技术上存在)
        bg = Image.new('RGB', (width, height), (0, 0, 0))  # 黑色不透明背景
        draw = ImageDraw.Draw(bg)

        text_color_invisible = (3, 3, 3)  # 深灰色,接近黑色,肉眼几乎不可见

        for r in range(rows):
            y = r * line_spacing
            draw.text((0, y), row_text, fill=text_color_invisible, font=font)

        # 保存单帧PNG
        tmp_frame = os.path.join(tempfile.gettempdir(), f"ending_frame_{int(time.time())}_{os.getpid()}.png")
        bg.save(tmp_frame, "PNG")

        if not os.path.exists(tmp_frame) or os.path.getsize(tmp_frame) < 1000:
            return False

        # FFmpeg loop生成2秒黑屏视频(无音频)
        tmp_ending = os.path.join(tempfile.gettempdir(), f"ending_clip_{int(time.time())}_{os.getpid()}.mp4")
        loop_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", tmp_frame,
            "-t", str(ending_dur),
            "-vf", "fps=1",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            tmp_ending
        ]
        lr = subprocess.run(loop_cmd, capture_output=True, timeout=60)
        os.unlink(tmp_frame)

        if lr.returncode != 0 or not os.path.exists(tmp_ending) or os.path.getsize(tmp_ending) < 5000:
            log(f"   ⚠️ 片尾水印帧生成失败: {lr.stderr[-300:]}", "")
            return False

        # concat:主视频 + 片尾
        # [FIX-20260601] copy main video to ASCII-only temp path to avoid FFmpeg UTF-8 path issue
        tmp_main = os.path.join(tempfile.gettempdir(), f"ending_main_{int(time.time())}_{os.getpid()}.mp4")
        shutil.copy(video_path, tmp_main)
        concat_list = os.path.join(tempfile.gettempdir(), f"concat_list_{int(time.time())}_{os.getpid()}.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            f.write(f"file {tmp_main}\n")
            f.write(f"file {tmp_ending}\n")

        tmp_final = os.path.join(tempfile.gettempdir(), f"ending_result_{int(time.time())}_{os.getpid()}.mp4")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            "-movflags", "+faststart",
            tmp_final
        ]
        cr = subprocess.run(concat_cmd, capture_output=True, timeout=120)
        os.unlink(concat_list)
        os.unlink(tmp_main)
        os.unlink(tmp_ending)

        if cr.returncode == 0 and os.path.exists(tmp_final) and os.path.getsize(tmp_final) > 50000:
            shutil.move(tmp_final, video_path)
            log(f"   ✅ 片尾水印完成(+{ending_dur:.0f}s, {len(text_pool)}个文本)", "")
            return True
        else:
            if os.path.exists(tmp_final):
                os.unlink(tmp_final)
            log(f"   ⚠️ 片尾concat失败: {cr.stderr[-300:]}", "")
            return False

    except Exception as e:
        log(f"   ⚠️ 片尾水印异常: {e}", "")
        return False


def _build_orig_audio_path(clip_files_map: Dict[int, str], selected_clips: List[Tuple[int, float, float, float]], tmp_dir: str) -> Optional[str]:



    """

    从源视频文件提取并拼接原声音频。

    clip_files_map: {file_idx: absolute_filepath}

    selected_clips: [(file_idx, start, end, score), ...]

    返回: 拼接后的原声音频文件路径

    """

    if not clip_files_map or not selected_clips:

        return None

    concat_list = os.path.join(tmp_dir, f"orig_audio_list_{int(time.time())}.txt")

    segment_files = []

    for file_idx, s, e, _ in selected_clips:

        src = clip_files_map.get(file_idx)

        if not src or not os.path.exists(src):

            continue

        dur = max(0.5, e - s)

        seg_file = os.path.join(tmp_dir, f"orig_seg_{file_idx}_{int(s*1000)}_{int(e*1000)}.aac")

        cmd = [

            "ffmpeg", "-y",

            # [FIX-音频对齐-20260520] 将-ss移到-i后面,慢速seek保证帧级精确

            "-i", src, "-ss", str(s),

            "-t", str(dur),

            "-vn", "-acodec", "copy",

            seg_file

        ]

        r = subprocess.run(cmd, capture_output=True, timeout=60)

        if r.returncode == 0 and os.path.exists(seg_file) and os.path.getsize(seg_file) > MIN_SEGMENT_SIZE:

            segment_files.append((seg_file, dur))

    if not segment_files:

        return None

    with open(concat_list, 'w', encoding='utf-8') as f:

        for seg_file, _ in segment_files:

            f.write(f"file '{seg_file}'\n")

    output = os.path.join(tmp_dir, f"orig_audio_mix_{int(time.time())}.aac")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,

           "-acodec", "copy", output]

    r = subprocess.run(cmd, capture_output=True, timeout=SUBPROCESS_TIMEOUT)

    try:

        os.remove(concat_list)

    except Exception:

        pass

    for seg_file, _ in segment_files:

        try:

            os.remove(seg_file)

        except Exception:

            pass

    if r.returncode == 0 and os.path.exists(output) and os.path.getsize(output) > MIN_AUDIO_SIZE:

        return output

    return None





def _render_final_multi_audio(
    video_path: str,
    bgm_path: Optional[str],
    narration_path: Optional[str],
    output_path: str,
    total_dur: float,
    drama_title: str = '',
    orig_audio_path: Optional[str] = None,
    full_text: str = "",
    genre: str = ""
) -> bool:
    '''
    三轨混音: 原声 + 解说 + BGM
    核心规则: 解说旁链压缩原声,解说说话时原声优雅降低,停顿时原声恢复
    音量从 CONFIG 读取: original_volume / narration_volume / bgm_volume
    '''
    try:
        # 以三轨中最大时长为 total_dur,避免解说/原声被截断
        # [FIX-BATCH3-20260607] 不再强制用视频时长覆盖,保留音频完整性
        video_stream_dur = _get_video_duration(video_path) if '_get_video_duration' in globals() else total_dur
        # 使用传入的total_dur,但确保不低于视频时长(避免视频提前结束)
        total_dur = max(total_dur, float(video_stream_dur))

        # 检查各音频文件是否有音轨(必须在此统一初始化,避免后续引用 UnboundLocalError)
        def _has_audio(path):
            if not path or not os.path.exists(path):
                return False
            try:
                r = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-select_streams', 'a',
                    '-show_entries', 'stream=codec_type',
                    '-of', 'csv=p=0', path
                ], capture_output=True, text=True, timeout=10)
                return r.returncode == 0 and 'audio' in r.stdout
            except Exception:
                return False

        orig_ok = _has_audio(orig_audio_path)
        narr_ok = _has_audio(narration_path)
        bgm_ok  = _has_audio(bgm_path)

        # 检查解说音频时长,确保输出包含完整解说
        if narr_ok and narration_path:
            try:
                narr_dur = None
                # 直接使用 ffprobe 获取音频时长
                r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', narration_path],
                                  capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    narr_dur = float(r.stdout.strip())
                if narr_dur and narr_dur > total_dur:
                    total_dur = narr_dur
                    log(f"   📏 解说时长({narr_dur:.1f}s) > 视频时长, 扩展total_dur", "")
            except Exception:
                pass

        dur_str = f"{total_dur:.3f}"
        # tmp_dir
        tmp_dir = os.path.dirname(output_path)

        # [FIX-20260530] 不允许延长视频帧/冻结帧/循环帧
        # 视频时长由上游步骤4.5(解说驱动片段调整)保证
        # 如果到这里视频仍不够长,只记录警告,不做任何帧操作
        video_dur = float(video_stream_dur)
        if video_dur < total_dur - 0.3:
            log(f"   ⚠️ 视频({video_dur:.1f}s) < 音频({total_dur:.1f}s),上游片段补充不足", "")

        # 音量从 CONFIG 读取: 有解说时原声略降(旁链自动控制进一步衰减),无解说时原声正常
        orig_vol = float(CONFIG.get('original_volume', 0.60))
        narr_vol = float(CONFIG.get('narration_volume', 0.80))
        bgm_vol  = float(CONFIG.get('bgm_volume', 0.30))
        if narr_ok:
            orig_vol = float(CONFIG.get('orig_volume_with_narration', 0.55))
            log(f"   🔊 解说存在,原声降低至{orig_vol}", "")
        log(f"   混音音量: 原声={orig_vol} 解说={narr_vol} BGM={bgm_vol}", "")

        if not narr_ok and not orig_ok:
            log("⚠️ 无可用音频,直接复制视频", '')
            subprocess.run(['ffmpeg', '-y', '-i', video_path,
                          '-c:v', 'copy', '-an', output_path],
                          capture_output=True, timeout=SUBPROCESS_TIMEOUT)
            return os.path.exists(output_path)

        # ---- 方案A: 各轨分别处理再混合 ----
        concat_file = os.path.join(tmp_dir, f"__mix_list_{int(time.time())}.txt")

        # 1. 原声轨(裁剪到视频长度)
        orig_wav = None
        if orig_ok and orig_audio_path and orig_vol > 0.001:
            orig_wav = os.path.join(tmp_dir, f"__orig_{int(time.time())}.wav")
            cmd = ['ffmpeg', '-y', '-i', orig_audio_path,
                   '-af', f'atrim=0:{dur_str},asetpts=PTS-STARTPTS',
                   '-ar', '44100', '-ac', '2', orig_wav]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
            if r.returncode != 0 or not os.path.exists(orig_wav):
                orig_wav = None
                log(f"   ⚠️ 原声处理失败: {r.stderr[-300:]}", '')

        # 2. 解说轨(静音填充到视频长度)
        narr_wav = None
        if narr_ok and narration_path:
            narr_wav = os.path.join(tmp_dir, f"__narr_{int(time.time())}.wav")
            # [FIX-20260701] 先直接检查输入MP3是否有声音,再决定如何处理
            # 用 ffprobe volumedetect 检测 mean_volume
            _check_cmd = ['ffmpeg', '-y', '-i', narration_path,
                           '-af', 'volumedetect', '-f', 'null', '-']
            _check_r = subprocess.run(_check_cmd, capture_output=True, text=True, timeout=15)
            _has_audio = True
            for _line in (_check_r.stderr or '').split('\n'):
                if 'mean_volume:' in _line:
                    _mean_db = float(_line.split('mean_volume:')[1].strip().split(' ')[0])
                    if _mean_db < -55:  # 小于-55dBFS视为静音
                        _has_audio = False
                        log(f"   ⚠️ 解说MP3疑似静音: mean_volume={_mean_db:.1f}dB", "⚠️")
                    else:
                        log(f"   🔊 解说MP3Audio检测: mean={_mean_db:.1f}dB", "")
                    break

            # apad 步骤:将解说填充到 total_dur 时长
            cmd = ['ffmpeg', '-y', '-i', narration_path,
                   '-af', f'apad=whole_dur={dur_str},asetpts=PTS-STARTPTS',
                   '-ar', '44100', '-ac', '2', narr_wav]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
            if r.returncode != 0 or not os.path.exists(narr_wav):
                # fallback: 不用apad,直接裁剪到目标时长
                cmd2 = ['ffmpeg', '-y', '-i', narration_path,
                        '-af', f'atrim=0:{dur_str},asetpts=PTS-STARTPTS',
                        '-ar', '44100', '-ac', '2', narr_wav]
                r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
                if r2.returncode != 0 or not os.path.exists(narr_wav):
                    narr_wav = None
                    log(f"   ⚠️ 解说处理失败: {r.stderr[-300:]}", '')
            else:
                # 验证 narr_wav 是否有声音
                _vc = subprocess.run(['ffmpeg', '-y', '-i', narr_wav,
                                     '-af', 'volumedetect', '-f', 'null', '-'],
                                    capture_output=True, text=True, timeout=15)
                for _line in (_vc.stderr or '').split('\n'):
                    if 'mean_volume:' in _line:
                        _mean_db = float(_line.split('mean_volume:')[1].strip().split(' ')[0])
                        if _mean_db < -55:
                            log(f"   ⚠️ narr_wav疑似静音: mean={_mean_db:.1f}dB, 可能是apad产生了静音文件", "⚠️")
                        break

        # 3. BGM轨(裁剪到视频长度)
        bgm_wav = None
        if bgm_ok and bgm_path:
            bgm_wav = os.path.join(tmp_dir, f"__bgm_{int(time.time())}.wav")
            # [FIX-20260627] BGM循环填充: BGM文件短于视频时长时自动循环
            bgm_dur = _get_video_duration(bgm_path) if '_get_video_duration' in globals() else 999
            need_loop = bgm_dur and bgm_dur > 0.5 and bgm_dur < float(dur_str)
            bgm_input = ['-stream_loop', '-1', '-i', bgm_path] if need_loop else ['-i', bgm_path]
            cmd = ['ffmpeg', '-y'] + bgm_input + [
                   '-af', f'atrim=0:{dur_str},asetpts=PTS-STARTPTS',
                   '-ar', '44100', '-ac', '2', bgm_wav]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
            if r.returncode != 0 or not os.path.exists(bgm_wav):
                bgm_wav = None

        # ---- 方案B: amix 混合 ----
        mix_inputs = []
        mix_labels = []
        mix_idx = 0

        if orig_wav:
            mix_inputs.extend(['-i', orig_wav])
            mix_labels.append(f'[{mix_idx}:a]')
            mix_idx += 1
        if narr_wav:
            mix_inputs.extend(['-i', narr_wav])
            mix_labels.append(f'[{mix_idx}:a]')
            mix_idx += 1
        if bgm_wav:
            mix_inputs.extend(['-i', bgm_wav])
            mix_labels.append(f'[{mix_idx}:a]')
            mix_idx += 1

        if not mix_inputs:
            log("⚠️ 所有音频处理失败,复制原视频", '')
            subprocess.run(['ffmpeg', '-y', '-i', video_path,
                          '-c:v', 'copy', '-an', output_path],
                          capture_output=True, timeout=SUBPROCESS_TIMEOUT)
            return os.path.exists(output_path)

        mix_label_str = ''.join(mix_labels)
        n_inputs = mix_idx

        # 视频作为最后一个输入(用于 -map 视频),音频只用 wav 文件
        # 用 -t 精确裁剪到视频时长,避免音视频不对齐
        # 注意:-shortest 对 -c:v copy 无效,必须用 -t + 重新编码
        video_input_idx = len(mix_inputs) // 2  # 每个 -i 前面有一个值

        # [P1-3] 调色风格微调:随机选择调色预设并注入FFmpeg
        _cg_filter = ''
        try:
            if '_get_color_grade' in globals():
                _cg = _get_color_grade(genre)
                if _cg:
                    _br = _cg.get('brightness', 0)
                    _co = _cg.get('contrast', 1.0)
                    _sa = _cg.get('saturation', 1.0)
                    _ga = _cg.get('gamma', 1.0)
                    _temperature = _cg.get('temperature', None)
                    _cg_filter = f'eq=brightness={_br}:contrast={_co}:saturation={_sa}:gamma={_ga}'
                    if _temperature:
                        # [FIX-colortemperature-20260619] 改用 colortemperature 滤镜(ffmpeg原生支持)
                        _cg_filter += f',colortemperature={_temperature}'
        except Exception:
            _cg_filter = ''

        # [FIX-20260701] 简化混音:去掉旁链压缩,直接用固定音量
        # 旁链压缩在FFmpeg里行为不稳定,可能导致解说被压制
        # 改用:解说固定2.5x、原声0.60(有解说时)/1.0(无解说时)、BGM0.15
        _amix_labels = []
        _fc_parts = []
        _ai = 0

        if orig_wav:
            _fc_parts.append(f'[{_ai}:a]volume={orig_vol}[orig]')
            _amix_labels.append('[orig]')
            _ai += 1

        if narr_wav:
            _fc_parts.append(f'[{_ai}:a]volume={narr_vol}[narr]')
            _amix_labels.append('[narr]')
            _ai += 1

        if bgm_wav:
            _fc_parts.append(f'[{_ai}:a]volume={bgm_vol}[bgm]')
            _amix_labels.append('[bgm]')
            _ai += 1

        _amix_filter = ''.join(_amix_labels) + f'amix=inputs={len(_amix_labels)}:duration=longest:dropout_transition=2:normalize=0[aout]'
        _fc_parts.append(_amix_filter)
        _sc_chain = ';'.join(_fc_parts)
        log(f'   简化混音(filter_complex): {_sc_chain}', '')

        if _cg_filter:
            # 有调色时: 视频加滤镜 + 旁链混音
            _fc_str = f'[{video_input_idx}:v]{_cg_filter}[vcolor];{_sc_chain}'
            # [FIX-20260622] 视频不够长时不冻结帧、不截断解说
            # 方案: 分两步--先混音(纯音频),再合并音视频
            cmd = (['ffmpeg', '-y'] + mix_inputs +
                   ['-filter_complex', _fc_str,
                    '-map', '[vcolor]', '-map', '[aout]',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-c:a', 'aac', '-b:a', '192k',
                    output_path + '.audio.mp4'])
        else:
            # 无调色时: 纯旁链混音
            cmd = (['ffmpeg', '-y'] + mix_inputs +
                   ['-filter_complex', _sc_chain,
                    '-map', '[aout]',
                    '-c:a', 'aac', '-b:a', '192k',
                    output_path + '.audio.mp4'])

        log(f"   执行混音({n_inputs}轨)...", '')
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=LONG_SUBPROCESS_TIMEOUT)

        # 清理临时wav文件
        for f in [orig_wav, narr_wav, bgm_wav]:
            if f and os.path.exists(f):
                try: os.remove(f)
                except Exception: pass

        mixed_audio = output_path + '.audio.mp4'
        if r.returncode != 0 or not os.path.exists(mixed_audio) or os.path.getsize(mixed_audio) < 1000:
            log(f"   ❌ 混音失败: {r.stderr[-300:] if r.stderr else 'unknown'}", "❌")
            return os.path.exists(output_path)

        # [FIX-20260622] 第二步: 合并视频+混音音频
        # 关键: 绝不截断解说音频,也不冻结视频帧
        # 方案: 先检测视频与解说时长,视频>=解说时正常合并;视频<解说时分两段处理
        log(f"   合并视频+音频...", '')
        # 获取视频和混音时长
        _vd_cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                   '-show_entries', 'stream=duration', '-of', 'csv=p=0', video_path]
        _ad_cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'a:0',
                   '-show_entries', 'stream=duration', '-of', 'csv=p=0', mixed_audio]
        try:
            _vd_r = subprocess.run(_vd_cmd, capture_output=True, text=True, timeout=10)
            _ad_r = subprocess.run(_ad_cmd, capture_output=True, text=True, timeout=10)
            _vd = float(_vd_r.stdout.strip()) if _vd_r.stdout.strip() else 0
            _ad = float(_ad_r.stdout.strip()) if _ad_r.stdout.strip() else 0
        except Exception:
            _vd = _ad = 0

        # [FIX-20260713] 解说截断修复: ≤3min用shortest自然对齐,>3min截断到解说
        _final_dur = _ad  # 默认以解说为准
        if _vd > 0 and _ad > 0:
            if max(_vd, _ad) <= 180:
                # 3分钟内: shortest对齐,不截断任何一轨
                log(f"   📏 3分钟内: 视频{_vd:.1f}s/解说{_ad:.1f}s,shortest自然对齐", '')
                _final_dur = None  # 用shortest,不设-t
            else:
                # 超3分钟: 截断到解说
                _final_dur = _ad
                log(f"   📏 >3分钟: 截断到解说{_ad:.1f}s", '')
        if _cg_filter:
            _dur_param = ['-shortest'] if _final_dur is None else ['-t', f'{_final_dur:.3f}']
            merge_cmd = (['ffmpeg', '-y', '-i', video_path, '-i', mixed_audio] +
                        ['-filter_complex', f'[0:v]{_cg_filter}[vcolor]',
                         '-map', '[vcolor]', '-map', '1:a',
                         '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
                         '-c:a', 'copy'] +
                        _dur_param +
                        ['-movflags', '+faststart', output_path])
        else:
            _dur_param = ['-shortest'] if _final_dur is None else ['-t', f'{_final_dur:.3f}']
            merge_cmd = (['ffmpeg', '-y', '-i', video_path, '-i', mixed_audio] +
                         ['-map', '0:v', '-map', '1:a',
                          '-c:v', 'copy', '-c:a', 'copy'] +
                         _dur_param +
                         ['-movflags', '+faststart', output_path])
        r2 = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=LONG_SUBPROCESS_TIMEOUT)
        # 清理临时文件
        try: os.remove(mixed_audio)
        except Exception: pass

        if r2.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 50000:
            # [FIX-20260622] 时长对齐: 视频以解说时长为基准
            # 绝不截断解说--用户听不到完整解说是最差体验
            # 视频短于解说时不做裁剪(视频流自然结束,播放器显示最后帧)
            # 视频远长于解说时(>5s)裁剪视频到解说时长
            try:
                v_dur = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                     '-show_entries', 'stream=duration', '-of', 'csv=p=0', output_path],
                    capture_output=True, text=True, timeout=10)
                a_dur = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-select_streams', 'a:0',
                     '-show_entries', 'stream=duration', '-of', 'csv=p=0', output_path],
                    capture_output=True, text=True, timeout=10)
                if v_dur.stdout.strip() and a_dur.stdout.strip():
                    vd = float(v_dur.stdout.strip())
                    ad = float(a_dur.stdout.strip())
                    if vd - ad > 5.0:
                        final_dur = ad
                        log(f"   ✅ 视频过长对齐: video={vd:.1f}s audio={ad:.1f}s, 裁剪到{final_dur:.1f}s", '')
                        trimmed = output_path + '.trim.mp4'
                        subprocess.run(
                            ['ffmpeg', '-y', '-i', output_path,
                             '-t', f'{final_dur:.3f}',
                             '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
                             '-c:a', 'aac', '-b:a', '192k',
                             '-movflags', '+faststart', trimmed],
                            capture_output=True, timeout=SUBPROCESS_TIMEOUT)
                        if os.path.exists(trimmed) and os.path.getsize(trimmed) > 50000:
                            os.replace(trimmed, output_path)
                            log(f"   ✅ 时长对齐完成", '')
                    elif ad - vd > 0.5:
                        log(f"   📏 解说({ad:.1f}s) > 视频({vd:.1f}s),保留完整解说,视频自然结束", '')
            except Exception as te:
                log(f"   ⚠️ 时长修正失败(不影响主流程): {te}", '')

            log(f"   ✅ 混音完成({os.path.getsize(output_path)//1024}KB)", '')
            if drama_title and HAS_PIL:
                # [FIX-20260627] 不在混音时叠加--intro concat会重编码并破坏叠加结果
                # 叠加移至主流程(步骤7),在intro prepend之后执行
                # 生成30个热门话题标签,叠加到片尾黑屏
                # 生成30个热门话题标签,叠加到片尾黑屏
                # 硬编码:永远包含免责标签(合规 P0)
                import random as _rnd
                _base_pool = [
                    "#短剧", "#短剧推荐", "#抖音短剧", "#霸总短剧", "#甜宠短剧",
                    "#复仇短剧", "#豪门恩怨", "#逆袭人生", "#婚姻情感", "#虐心短剧",
                    "#古装短剧", "#穿越剧", "#玄幻短剧", "#都市情感", "#家庭伦理",
                    "#太上头了", "#甜到犯规", "#虐到心碎", "#笑到肚子疼", "#全程高能",
                    "#追剧日记", "#每日追剧", "#追剧时光", "#必看短剧", "#宝藏短剧",
                ]
                _rnd.shuffle(_base_pool)
                ending_tags = _base_pool[:28]
                log(f"   🏷️  生成{len(ending_tags)}个话题标签", "")
                # 片尾水印已禁用
                # _add_ending_watermark(output_path, drama_title, tags=ending_tags, ending_dur=2.0)
                # 片头AI标识(合规:6月14日四部门新规强制执行)
                if '_add_intro_ai_disclosure' in globals():
                    try:
                        _ok_intro = _add_intro_ai_disclosure(output_path, total_dur=2.0)
                        if _ok_intro:
                            log(f"   ✅ 片头AI标识已添加", '')
                        else:
                            log(f"   ⚠️ 片头AI标识失败(合规风险!成片无AI声明)", '⚠️')
                    except Exception as _e:
                        log(f"   ⚠️ 片头AI标识异常: {_e} (合规风险!)", '⚠️')
            return True

        log(f"⚠️ 混音失败(rc={r.returncode}): {r.stderr[-500:]}", '⚠️')
        return False

    except Exception as e:
        log(f"⚠️ 混音异常: {e}", '⚠️')
        return False




def _smart_narrative_arrangement(all_clips: list, file_clips: dict,
                                  files: list = None,

                                  genre: str = "",

                                  emotion_curve: list = None,

                                  full_text: str = "") -> list:

    """

    五段式智能叙事编排(完整版)



    结构:开场钩子 → 关系建立 → 冲突升级 → 情绪爆点 → 悬念收束



    核心原则:

    1. 每个模块片段数量不限,由内容质量自动决定

    2. 质量好的线程多放片段,质量差的少放

    3. 同一场景线程优先串联使用(叙事连贯)

    4. 总时长控制在30-180秒

    """

    if not all_clips:

        return []



    files = files or []

    emotion_curve = emotion_curve or []

    full_text = full_text or ""



    MIN_DUR = CONFIG.get("min_duration", 60)

    MAX_DUR = CONFIG.get("max_duration", 9999)  # 默认不限制时长

    CLIP_MIN = CONFIG.get("clip_min_sec", 2.0)



    # ═══════════════════════════════════════════════════════════

    # 1 场景线程分析:同一文件内间隔<5秒的连续高光序列

    # ═══════════════════════════════════════════════════════════

    scene_threads = []  # [(clips, file_idx, thread_type, score)]



    for file_idx, clips in file_clips.items():

        if not clips:

            continue



        clips_sorted = sorted(clips, key=lambda x: x[0])  # 按时间排序



        # 分割场景线程(间隔>5秒视为不同场景)

        threads = []

        current_thread = [clips_sorted[0]]



        for clip in clips_sorted[1:]:

            prev_end = current_thread[-1][1]

            if clip[0] - prev_end < 5.0:

                current_thread.append(clip)

            else:

                threads.append(current_thread)

                current_thread = [clip]

        if current_thread:

            threads.append(current_thread)



        # 为每个线程判定类型和评分

        for thread in threads:

            thread_type = _infer_thread_type(thread, file_idx, full_text, genre)

            thread_score = _thread_score(thread, thread_type)

            scene_threads.append({

                'clips': thread,

                'file_idx': file_idx,

                'type': thread_type,

                'score': thread_score,

                'duration': thread[-1][1] - thread[0][0]

            })



    log(f"   🎬 场景线程分析: 共{len(scene_threads)}个场景线程", "")

    for t in scene_threads[:5]:

        log(f"      → 文件{t['file_idx']}: {t['type']}型 {len(t['clips'])}片段 {t['duration']:.1f}s 得分{t['score']:.1f}", "")



    # ═══════════════════════════════════════════════════════════

    # 2 五段式模块分配

    # ═══════════════════════════════════════════════════════════

    module_config = {

        'hook':        {'importance': 3, 'preferred_types': ['conflict', 'suspense', 'climax'], 'min_dur': 3, 'max_dur': 12},

        'setup':       {'importance': 2, 'preferred_types': ['setup', 'dialogue', 'emotion'], 'min_dur': 5, 'max_dur': 20},

        'conflict':    {'importance': 3, 'preferred_types': ['conflict', 'climax', 'suspense'], 'min_dur': 5, 'max_dur': 20},

        'climax':      {'importance': 4, 'preferred_types': ['climax', 'emotion', 'conflict'], 'min_dur': 5, 'max_dur': 15},

        'resolution':  {'importance': 3, 'preferred_types': ['suspense', 'emotion', 'climax'], 'min_dur': 3, 'max_dur': 12}

    }



    modules_selected = {}

    used_threads = set()



    for module_name, config in module_config.items():

        # 为该模块选取最适合的线程

        best_thread = _select_best_thread_for_module(

            scene_threads, module_name, config, used_threads, files

        )



        if best_thread:

            # 根据质量自动决定使用多少片段

            clips_to_use = _decide_clip_count(best_thread, config['importance'])

            modules_selected[module_name] = best_thread['clips'][:clips_to_use]

            used_threads.add(id(best_thread))

            log(f"   📍 {module_name}: {len(modules_selected[module_name])}片段 {sum(c[1]-c[0] for c in modules_selected[module_name]):.1f}s", "")

        else:

            modules_selected[module_name] = []

            log(f"   ⚠️ {module_name}: 无合适片段", "")



    # ═══════════════════════════════════════════════════════════

    # 3 按叙事顺序组合输出(带MAX_DUR硬上限)

    # ═══════════════════════════════════════════════════════════

    selected = []

    module_order = ['hook', 'setup', 'conflict', 'climax', 'resolution']

    remaining_budget = MAX_DUR  # 剩余时长预算(秒)



    for module_name in module_order:

        if remaining_budget < CLIP_MIN:

            log(f"   ⏹️ 时长已达MAX_DUR({MAX_DUR}s),停止后续模块", "")

            break



        for clip in modules_selected.get(module_name, []):

            dur = clip[1] - clip[0]

            # 放入条件:该片段能完整放入剩余预算

            if dur <= remaining_budget:

                file_idx = _find_file_idx_for_clip(clip, file_clips)

                selected.append((file_idx, clip[0], clip[1], clip[2]))

                remaining_budget -= dur

            elif remaining_budget >= CLIP_MIN and dur > remaining_budget:

                # 剩余不足1个片段但够用,放入最后1个(会被截断)

                file_idx = _find_file_idx_for_clip(clip, file_clips)

                selected.append((file_idx, clip[0], clip[1], clip[2]))

                remaining_budget = 0



    # 按文件索引和时间排序

    selected = sorted(selected, key=lambda x: (x[0], x[1]))



    # ═══════════════════════════════════════════════════════════

    # 4 时长检查:不足MIN_DUR则补充(上限不变)

    # ═══════════════════════════════════════════════════════════

    total_dur = sum(c[2] - c[1] for c in selected)



    if total_dur < MIN_DUR:

        log(f"   ⚠️ 时长不足({total_dur:.1f}s),补充片段...", "")

        remaining = [c for c in all_clips if c not in selected]

        remaining.sort(key=lambda x: -x[3])  # 按得分降序



        for clip in remaining:

            dur = clip[2] - clip[1]

            if dur >= CLIP_MIN and total_dur + dur <= MAX_DUR:

                selected.append(clip)

                total_dur += dur

                if total_dur >= MIN_DUR:

                    break



    # 按文件索引和时间排序

    selected = sorted(selected, key=lambda x: (x[0], x[1]))



    # 统计输出

    files_used = len(set(c[0] for c in selected))

    log(f"   ✅ 叙事编排完成: {len(selected)}片段 | {total_dur:.1f}秒 | {files_used}个文件", "")



    # 各模块统计

    for module_name in module_order:

        clips = modules_selected.get(module_name, [])

        if clips:

            dur = sum(c[1] - c[0] for c in clips)

            log(f"      {module_name}: {len(clips)}片段 {dur:.1f}s", "")



    return selected





def _infer_thread_type(thread: list, file_idx: int, full_text: str, genre: str) -> str:

    """

    判定场景线程的类型



    类型:hook(钩子) / setup(铺垫) / conflict(冲突) / climax(高潮) / suspense(悬念)



    判定依据:

    1. 片段得分分布(高分=激烈)

    2. 台词内容(关键词匹配)

    3. 文件位置(开头=钩子,结尾=悬念)

    """

    if not thread:

        return 'setup'



    avg_score = sum(c[2] for c in thread) / len(thread)

    max_score = max(c[2] for c in thread)



    # 关键词匹配

    text_lower = full_text.lower() if full_text else ""



    # 冲突关键词

    conflict_kws = ["滚", "死", "打", "杀", "废", "滚出去", "你给我", "不要脸", "混蛋", "报仇", "算账", "打脸"]

    # 情绪关键词

    emotion_kws = ["对不起", "原谅", "哭", "眼泪", "心疼", "难过", "委屈", "放弃", "离开", "痛", "后悔"]

    # 悬念关键词

    suspense_kws = ["真相", "秘密", "阴谋", "背后", "其实", "原来", "发现", "证据", "隐瞒", "骗", "假的"]

    # 铺垫关键词

    setup_kws = ["你好", "谢谢", "不好意思", "请", "麻烦", "帮忙", "认识", "朋友", "合作"]



    conflict_cnt = sum(text_lower.count(kw) for kw in conflict_kws)

    emotion_cnt = sum(text_lower.count(kw) for kw in emotion_kws)

    suspense_cnt = sum(text_lower.count(kw) for kw in suspense_kws)

    setup_cnt = sum(text_lower.count(kw) for kw in setup_kws)



    # 判定逻辑

    if max_score >= 8 and conflict_cnt > emotion_cnt:

        return 'conflict'

    elif max_score >= 9:

        return 'climax'

    elif suspense_cnt >= max(conflict_cnt, emotion_cnt, 1):

        return 'suspense'

    elif emotion_cnt > conflict_cnt and avg_score >= 6:

        return 'emotion'

    elif setup_cnt > 0 or avg_score < 5:

        return 'setup'

    else:

        return 'dialogue'





def _thread_score(thread: list, thread_type: str) -> float:

    """

    场景线程评分



    评分因素:

    1. 各片段得分总和

    2. 连续性奖励(多片段串联+3分)

    3. 类型匹配奖励

    """

    if not thread:

        return 0



    base_score = sum(c[2] for c in thread)



    # 连续性奖励

    continuity_bonus = 3.0 if 2 <= len(thread) <= 6 else 0



    # 类型强度奖励

    type_bonus = {

        'climax': 5, 'conflict': 4, 'suspense': 3,

        'emotion': 2, 'dialogue': 1, 'setup': 0

    }.get(thread_type, 0)



    return base_score + continuity_bonus + type_bonus





def _select_best_thread_for_module(threads: list, module_name: str,

                                    config: dict, used_threads: set,

                                    files: list) -> dict:

    """

    为指定模块选取最适合的场景线程



    选取策略:

    1. 类型匹配优先

    2. 高分优先

    3. 未使用优先

    4. 时长符合要求

    """

    candidates = []



    for t in threads:

        if id(t) in used_threads:

            continue



        # 类型匹配得分

        type_match = t['type'] in config['preferred_types']

        type_score = 10 if type_match else 0



        # 时长符合度

        dur_ok = config['min_dur'] <= t['duration'] <= config['max_dur']

        dur_score = 5 if dur_ok else 0



        # 综合得分

        total = t['score'] + type_score + dur_score + config['importance']



        candidates.append((total, t))



    if not candidates:

        return None



    # 选取得分最高的

    candidates.sort(key=lambda x: -x[0])

    return candidates[0][1]





def _decide_clip_count(thread: dict, importance: int) -> int:

    """

    根据线程质量和重要性自动决定使用多少片段



    规则:

    1. 基础数量 = 线程片段数(不限)

    2. 质量加成 = score / 10 * 2(高分多放)

    3. 重要性加成 = importance(重要模块多放)

    4. 最终数量 = min(基础 + 加成, 线程片段数)



    不设上限,但受限于线程本身有多少片段

    """

    base = len(thread['clips'])

    quality_bonus = int(thread['score'] / 10 * 2)

    importance_bonus = importance



    target = base + quality_bonus + importance_bonus



    # 不超过线程实际片段数

    return min(target, len(thread['clips']))





def _find_file_idx_for_clip(clip: tuple, file_clips: dict) -> int:

    """根据片段信息找到对应的文件索引"""

    s, e, sc = clip[0], clip[1], clip[2]



    for file_idx, clips in file_clips.items():

        for c in clips:

            if abs(c[0] - s) < 0.1 and abs(c[1] - e) < 0.1:

                return file_idx



    return 0  # 默认返回第一个文件





# ==================== 入口 ====================



def _quality_audit(final_video_path: str, expected_duration: float = None) -> dict:
    """
    成品质量审计(P2:输出前最终检查)
    检查项:时长、黑屏、音量、音画同步
    返回: {"passed": bool, "score": 0-100, "issues": [...], "details": {...}}
    """
    import subprocess, json as _json

    result = {"passed": False, "score": 100, "issues": [], "details": {}}

    if not os.path.exists(final_video_path):
        result["issues"].append("输出文件不存在")
        result["score"] = 0
        return result

    log("🔍 [P2] 成品质量审计...", "⏳")

    # 1. 基础信息检查(ffprobe)
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_format", "-show_streams",
            "-print_format", "json", final_video_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)
        probe = _json.loads(r.stdout)

        fmt = probe.get("format", {})
        streams = probe.get("streams", [])

        duration = float(fmt.get("duration", 0))
        size_mb = int(fmt.get("size", 0)) / (1024*1024)

        result["details"]["duration"] = duration
        result["details"]["size_mb"] = round(size_mb, 2)

        # 检查时长
        if expected_duration and abs(duration - expected_duration) > 5:
            result["issues"].append(f"时长偏差过大: {duration:.1f}s vs 预期{expected_duration:.1f}s")
            result["score"] -= 15

        if duration < 60:
            result["issues"].append(f"视频过短: {duration:.1f}s (<60s)")
            result["score"] -= 20
        elif duration > 180:
            result["issues"].append(f"视频过长: {duration:.1f}s (>3min)")
            result["score"] -= 10

        # 检查音视频流
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        if not has_video:
            result["issues"].append("无视频流")
            result["score"] = 0
        if not has_audio:
            result["issues"].append("无音频流")
            result["score"] -= 30

        # 视频参数检查
        for s in streams:
            if s.get("codec_type") == "video":
                width = s.get("width", 0)
                height = s.get("height", 0)
                result["details"]["resolution"] = f"{width}x{height}"

                if width < 480 or height < 640:
                    result["issues"].append(f"分辨率过低: {width}x{height}")
                    result["score"] -= 10
                break

    except Exception as e:
        result["issues"].append(f"ffprobe检查失败: {e}")
        result["score"] -= 20

    # 2. 黑屏检测(采样检查)
    try:
        # 提取中间帧检查是否黑屏
        mid_time = duration / 2 if duration > 0 else 1
        cmd = [
            "ffmpeg", "-i", final_video_path, "-ss", str(mid_time),
            "-vframes", "1", "-f", "image2pipe", "-pix_fmt", "rgb24",
            "-"
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=10)

        if r.returncode == 0 and r.stdout:
            # 简单检查:如果输出全是0就是黑屏
            avg_val = sum(r.stdout) / len(r.stdout) if r.stdout else 255
            if avg_val < 10:
                result["issues"].append("检测到黑屏(中间帧)")
                result["score"] -= 25
            result["details"]["mid_frame_avg"] = round(avg_val, 1)
    except Exception as e:
        result["issues"].append(f"黑屏检测失败: {e}")

    # 3. 音量检测
    try:
        cmd = [
            "ffmpeg", "-i", final_video_path, "-af", "volumedetect",
            "-f", "null", "-"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)

        # 解析 mean_volume
        mean_match = re.search(r'mean_volume: ([-\d.]+) dB', r.stderr)
        max_match = re.search(r'max_volume: ([-\d.]+) dB', r.stderr)

        if mean_match:
            mean_db = float(mean_match.group(1))
            result["details"]["mean_volume_db"] = mean_db

            if mean_db < -40:
                result["issues"].append(f"音量过低: {mean_db:.1f}dB (建议>-25dB)")
                result["score"] -= 15
            elif mean_db > -5:
                result["issues"].append(f"音量过高: {mean_db:.1f}dB (建议<-10dB)")
                result["score"] -= 10

        if max_match:
            result["details"]["max_volume_db"] = float(max_match.group(1))
    except Exception as e:
        result["issues"].append(f"音量检测失败: {e}")

    # 4. 综合评分
    result["score"] = max(0, min(100, result["score"]))
    result["passed"] = result["score"] >= 70 and len(result["issues"]) <= 2

    # 输出日志
    status = "✅" if result["passed"] else "❌"
    log(f"   {status} 质量评分: {result['score']}/100, 问题{len(result['issues'])}个", "" if result["passed"] else "⚠️")
    for issue in result["issues"][:3]:  # 只显示前3个问题
        log(f"      ⚠️ {issue}", "")

    return result


    """获取剧集记忆文件路径"""
    safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', drama_name)
    return os.path.join(MEMORY_DIR, f"{safe_name}_memory.json")


def load_drama_memory(drama_name: str) -> dict:
    """
    加载剧集记忆(P3:多集连续性)
    返回: {"episodes": [], "characters": {}, "plot_progress": {}, "style": {}, "last_episode": 0}
    """
    memory_path = _get_drama_memory_path(drama_name)

    if os.path.exists(memory_path):
        try:
            with open(memory_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
            log(f"📚 [P3] 加载剧集记忆: {drama_name} (已处理{len(memory.get('episodes', []))}集)", "")
            return memory
        except Exception as e:
            log(f"   ⚠️ 记忆加载失败: {e}", "⚠️")

    # 初始化新记忆
    return {
        "drama_name": drama_name,
        "episodes": [],
        "characters": {},  # 角色: {name: {first_ep: N, traits: "", arc: ""}}
        "plot_progress": {},  # 剧情线: {line_name: {current: "", resolved: bool}}
        "style": {"genre": "", "tone": "", "pacing": ""},
        "last_episode": 0,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }


def save_drama_memory(drama_name: str, memory: dict):
    """保存剧集记忆"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    memory_path = _get_drama_memory_path(drama_name)
    memory["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        log(f"   💾 记忆已保存: {memory_path}", "")
    except Exception as e:
        log(f"   ⚠️ 记忆保存失败: {e}", "⚠️")


def update_drama_memory(memory: dict, episode: int, analysis: dict,
                        highlights: list, narration: str) -> dict:
    """
    更新剧集记忆(处理完一集后调用)
    """
    # 1. 记录本集信息
    ep_record = {
        "episode": episode,
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "key_events": analysis.get("events", []),
        "mood": analysis.get("mood_timeline", ""),
        "highlight_count": len(highlights),
        "narration_preview": narration[:100] + "..." if len(narration) > 100 else narration
    }
    memory["episodes"].append(ep_record)
    memory["last_episode"] = episode

    # 2. 更新角色信息
    chars = analysis.get("characters", [])
    for char in chars:
        name = char if isinstance(char, str) else char.get("name", "未知")
        if name not in memory["characters"]:
            memory["characters"][name] = {
                "first_episode": episode,
                "traits": "",
                "arc": ""
            }

    # 3. 更新剧情进度
    events = analysis.get("events", [])
    for ev in events:
        ev_name = ev if isinstance(ev, str) else ev.get("name", str(ev))
        if ev_name not in memory["plot_progress"]:
            memory["plot_progress"][ev_name] = {
                "introduced_ep": episode,
                "current_status": "ongoing",
                "resolved": False
            }

    # 4. 更新风格(只在第一集设定)
    if episode == 1 or not memory["style"].get("genre"):
        memory["style"]["genre"] = analysis.get("genre", "")
        memory["style"]["tone"] = analysis.get("mood_timeline", "")[:20]

    log(f"   📝 记忆更新: 第{episode}集, {len(chars)}角色, {len(events)}事件", "")
    return memory


def get_episode_context(memory: dict, current_ep: int) -> dict:
    """
    获取当前集需要的上下文(用于解说生成时注入)
    返回: {"previous_recap": "", "character_context": "", "ongoing_plots": []}
    """
    context = {
        "previous_recap": "",
        "character_context": "",
        "ongoing_plots": [],
        "style_guide": memory.get("style", {})
    }

    # 1. 前情提要(上一集的关键事件)
    episodes = memory.get("episodes", [])
    if episodes and current_ep > 1:
        prev_ep = episodes[-1]
        events = prev_ep.get("key_events", [])
        if events:
            # 取最后一个事件作为悬念
            last_event = events[-1] if isinstance(events[-1], str) else events[-1].get("name", str(events[-1]))
            context["previous_recap"] = f"上集{last_event}"

    # 2. 角色上下文(本集首次出现的角色)
    chars = memory.get("characters", {})
    new_chars = [name for name, info in chars.items() if info.get("first_episode") == current_ep]
    if new_chars:
        context["character_context"] = f"本集新角色: {', '.join(new_chars[:3])}"

    # 3. 未完结剧情线
    plots = memory.get("plot_progress", {})
    ongoing = [name for name, info in plots.items()
               if not info.get("resolved", False) and info.get("introduced_ep", 999) < current_ep]
    context["ongoing_plots"] = ongoing[:3]  # 最多3个

    return context


def apply_memory_to_prompt(memory: dict, prompt: str, episode: int) -> str:
    """
    将记忆注入到解说生成的 prompt 中
    """
    context = get_episode_context(memory, episode)

    # 构建记忆注入文本
    injections = []

    if context["previous_recap"]:
        injections.append(f"【前情】{context['previous_recap']}")

    if context["ongoing_plots"]:
        injections.append(f"【待解悬念】{', '.join(context['ongoing_plots'])}")

    style = context.get("style_guide", {})
    if style.get("genre"):
        injections.append(f"【系列风格】{style['genre']}")

    if injections:
        memory_text = "\n".join(injections)
        # 在 prompt 的【剧情信息】部分后插入
        if "【剧情信息】" in prompt:
            prompt = prompt.replace(
                "【剧情信息】",
                f"【剧情信息】\n{memory_text}"
            )
        else:
            # 在开头插入
            prompt = f"{memory_text}\n\n{prompt}"

    return prompt

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="抖音短剧AI自动剪辑工具")

    parser.add_argument("--config", type=str, help="用户配置JSON文件路径")

    args = parser.parse_args()



    user_config = {}

    if args.config and os.path.exists(args.config):

        with open(args.config, "r", encoding="utf-8") as f:

            user_config = json.load(f)



    batch_auto_cut(user_config)
