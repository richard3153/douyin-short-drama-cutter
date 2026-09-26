# -*- coding: utf-8 -*-
"""配置合并器 - 支持用户自定义 / 智能检测 / 默认配置三层优先级"""
import json
import os
from typing import Any, Dict

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- 智能默认配置（来自 smart_config.json 的默认值）----
SMART_DEFAULTS: Dict[str, Any] = {
    "aspect_ratio": "9:16",
    "title_dur": 1.2,
    "end_dur": 1.6,
    "enable_asr": True,
    "asr_model": "medium",          # medium=更高识别精度
    "original_volume": 0.60,
    "narration_volume": 0.80,
    "bgm_volume": 0.30,
    "orig_vol": 0.25,
    "narr_vol": 0.80,
    "transition_type": "auto",
    "trans_dur": 0.5,
    "rhythm_style": "auto",
    "style_keywords": "",
    "subtitle_lang": "zh",
    "light_mood": "auto",
    "narrative_arrangement": "auto",
    "trailer_template": "reverse_hook",
    "color_grade": "auto",
    "module_hook": "hook_flash",
    "module_setup": "setup_fade",
    "module_conflict": "conflict_cut",
    "module_emotion": "emotion_fade",
    "module_climax": "climax_suspense",
    "camera_move": "auto",
    "use_whisper": False,           # 默认使用 whisper.cpp
    "use_chattts": True,
    "use_edge_tts": True,
    "use_gpt_sovits": False,
}


def is_user_customized(value: Any) -> bool:
    """判断值是否表示用户已明确设置（不是占位符）"""
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value and value != "" and value.lower() != "auto")
    if isinstance(value, (list, dict)):
        return bool(value)
    return False


def merge_config(
    user_config: Dict[str, Any],
    smart_config: Dict[str, Any],
    default_config: Dict[str, Any],
) -> Dict[str, Any]:
    """三层配置合并：用户自定义 > 智能检测 > 默认配置
    
    优先级规则：
    - 如果用户在 user_config 中明确设置了某参数（非 auto/空/None）→ 使用用户值，标记 source="user"
    - 否则如果智能检测提供了某参数 → 使用智能值，标记 source="smart"
    - 否则使用默认配置的值 → 标记 source="default"
    """
    result: Dict[str, Any] = {}
    
    # 从默认配置开始（通常来自 config.json）
    for key, value in default_config.items():
        if value is not None:
            result[key] = value
            result[f"{key}_source"] = "default"
    
    # 合并智能检测配置（覆盖默认值）
    for key, value in smart_config.items():
        if value is not None:
            result[key] = value
            result[f"{key}_source"] = "smart"
    
    # 合并用户自定义配置（最高优先级）
    for key, value in user_config.items():
        if is_user_customized(value):
            result[key] = value
            result[f"{key}_source"] = "user"
    
    return result


def get_final_config(user_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """生成最终配置：用户配置 + 智能默认值
    
    参数:
        user_config: 用户配置字典（来自 API 请求或 --config 文件）
    
    返回:
        合并后的完整配置字典
    """
    user_config = user_config or {}
    
    # 读取智能检测配置（如果有）
    smart_config: Dict[str, Any] = {}
    smart_config_path = os.path.join(PROJECT_ROOT, "smart_config.json")
    if os.path.exists(smart_config_path):
        try:
            with open(smart_config_path, encoding="utf-8") as f:
                smart_config = json.load(f)
        except Exception:
            pass
    
    # 合并三层配置
    return merge_config(user_config, smart_config, SMART_DEFAULTS.copy())


def load_user_config() -> Dict[str, Any]:
    """从 user_config.json 加载用户配置"""
    path = os.path.join(PROJECT_ROOT, "user_config.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
