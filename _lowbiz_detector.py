"""
低俗内容检测器 - 低俗违规源头规避与检测
检测维度: 解说文本 + 视频帧内容(通过BLIP2)
"""

import re
from typing import List, Dict

# ============================================================
# 维度一: 解说文本低俗关键词库
# ============================================================

# 【绝对禁止】- 出现即违规
PROHIBITED_WORDS = [
    # 性行为/性器官暗示
    "做爱", "上床", "啪啪", "呻吟", "喘息", "滚床单",
    "性爱", "裸", "脱光", "全裸", "一丝不挂", "玉体", "酮体",
    "私处", "阴部", "臀部", "大腿根", "胸脯", "奶子",
    "乳沟", "爆乳", "巨乳", "揉胸", "摸胸", "抓胸",
    "插入", "抽插", "润滑", "欲仙欲死", "欲罢不能",
    "娇喘", "春药", "催情", "自慰", "手淫", "口交", "肛交",
    "性交", "交媾", "精液", "射精",
    "云雨", "行房", "房事", "巫山", "床第之事",
    # 低俗行为描述
    "勾引", "勾搭", "勾栏", "青楼", "妓院", "出台",
    "情趣", "湿身", "湿透", "裸泳", "裸睡",
    "媚药", "迷奸", "下药", "灌醉", "猥亵", "猥琐",
    "调戏", "非礼", "轻薄", "狎昵", "宠幸", "侍寝",
    "偷窥", "窥视", "偷拍",
    # 贴身衣物
    "情趣内衣", "丝袜", "吊带袜", "蕾丝", "内裤", "胸罩",
    "肚兜", "亵衣", "亵裤",
    # 粗口/低俗
    "傻逼", "肏", "贱货", "婊子", "荡妇", "骚货",
    "操", "草泥马", "尼玛", "绿茶婊", "心机婊",
    # 暴力/血腥(短剧推广高风险)
    "血肉模糊", "脑浆", "开膛", "分尸", "碎尸", "虐杀",
    "割喉", "挖眼", "断肢", "肠子",
]

# 【警告词】- 需上下文判断,扣分而非直接禁止
WARNING_WORDS = [
    # 叙事词汇(正常用法,但需上下文判断)
    "高潮",
    # 身体敏感部位(中性词但易擦边)
    "身材", "曲线", "身材好", "丰满", "傲人", "凹凸", "韵味",
    "S曲线", "A4腰", "水蛇腰", "蜜桃臀", "大长腿", "长腿",
    "美腿", "香肩", "锁骨", "美背", "光滑",
    "翘臀", "细腰", "酥胸", "若隐若现",
    "曲线玲珑", "曼妙", "妖娆", "妩媚", "娇媚",
    # 暧昧场景词
    "暧昧", "独处", "共枕", "同眠", "亲密", "相拥", "抱紧",
    "肌肤", "肌肤之亲", "嘴唇", "吻", "热吻", "湿吻",
    "眼神", "勾人", "魅惑", "挑逗", "撩人", "撩拨",
    "诱惑", "色诱", "宽衣", "宽衣解带", "褪去", "褪下",
    "洗澡", "沐浴", "更衣", "换衣", "更衣室", "浴室",
    "同床", "共浴", "温存", "娇羞", "娇柔",
    "抚摸", "触碰", "滑过", "游走", "轻抚",
    "颤抖", "瘫软", "面红耳赤", "心跳加速",
    "闺房", "春宵", "入帐", "就寝",
    # 暴露服装
    "透视", "透视装", "露背", "露肩", "露脐", "低胸", "深V",
    "比基尼", "泳装", "紧身衣", "裹胸",
    "短裙", "超短裙", "开叉", "真空",
    "湿衫", "低腰裤",
]

# 违规内容等级
VIOLATION_LEVELS = {
    "PROHIBITED": {"score": -30, "level": "P0"},
    "WARNING": {"score": -10, "level": "P1"},
}


def check_narration_lowbiz(narration_text: str) -> Dict:
    """
    检查解说文本是否包含低俗内容

    Returns:
        {
            "has_violation": bool,
            "score_deduct": int,
            "violations": [{"type": str, "word": str, "level": str}],
            "has_warning": bool,
        }
    """
    if not narration_text:
        return {"has_violation": False, "score_deduct": 0, "violations": [], "has_warning": False}

    result = {
        "has_violation": False,
        "score_deduct": 0,
        "violations": [],
        "has_warning": False,
    }

    for word in PROHIBITED_WORDS:
        if word in narration_text:
            result["has_violation"] = True
            result["score_deduct"] += VIOLATION_LEVELS["PROHIBITED"]["score"]
            result["violations"].append({
                "type": "PROHIBITED",
                "word": word,
                "level": "P0",
            })

    for word in WARNING_WORDS:
        if word in narration_text:
            result["has_warning"] = True
            result["score_deduct"] += VIOLATION_LEVELS["WARNING"]["score"]
            result["violations"].append({
                "type": "WARNING",
                "word": word,
                "level": "P1",
            })

    return result


# ============================================================
# 维度二: BLIP2视频帧低俗内容检测
# ============================================================

# BLIP2 prompt - 用于提取可能低俗的画面内容
NSFW_BLIP_PROMPT = (
    "Describe this image briefly and objectively. "
    "Focus on: clothing, body exposure, physical contact between people, "
    "facial expressions, setting. Be neutral and factual."
)

# 低俗画面描述关键词（在BLIP2英文caption中匹配）
NSFW_ENGLISH_KEYWORDS = [
    # 暴露/擦边服装
    "bikini", "lingerie", "underwear", "bra", "panties", "thong", "garter belt",
    "stockings", "stocking", "fishnet", "see-through", "sheer", "transparent",
    "revealing", "low-cut", "cleavage", "bared", "bare chest", "exposed body",
    "wet clothes", "wet shirt", "wet clothing", "dripping wet",
    # 亲密/暧昧接触
    "kissing", "embracing", "hugging", "cuddling", "intimate", "sensual",
    "seductive", "provocative pose", "seductive pose", "sensual pose",
    "naked", "nude", "undressed", "half-naked", "topless",
    # 性暗示道具/场景
    "sex toy", "vibrator", "dildo", "condom", "bondage", "chains",
    "bedroom", "bed sheets", "bed",
]

# 高风险场景描述（在BLIP2 caption中匹配）
HIGH_RISK_SCENE_PATTERNS = [
    re.compile(r'\b(naked|nude|undressed)\b', re.I),
    re.compile(r'\b(bikini|lingerie|underwear|bra|panties|thong)\b', re.I),
    re.compile(r'\b(wet shirt|wet clothes|wet body|dripping wet)\b', re.I),
    re.compile(r'\b(topless|exposed|revealing)\b', re.I),
    re.compile(r'\b(seductive|provocative|sensual|intimate)\b', re.I),
    re.compile(r'\b(sex toy|vibrator)\b', re.I),
    re.compile(r'\b(bedroom|bed sheets)\b', re.I),
]


def check_frame_lowbiz(frame_caption: str) -> Dict:
    """
    检查单帧BLIP2描述是否包含低俗内容（英文caption双语匹配）

    Returns:
        {
            "has_violation": bool,
            "score_deduct": int,
            "matched_patterns": [str],
        }
    """
    if not frame_caption:
        return {"has_violation": False, "score_deduct": 0, "matched_patterns": []}

    caption_lower = frame_caption.lower()
    matched = []

    for pattern in HIGH_RISK_SCENE_PATTERNS:
        if pattern.search(caption_lower):
            matched.append(pattern.pattern)

    for keyword in NSFW_ENGLISH_KEYWORDS:
        if keyword.lower() in caption_lower:
            pattern_str = re.escape(keyword)
            if pattern_str not in matched:
                matched.append(keyword)

    score_deduct = len(matched) * 8  # 每匹配一个关键词扣8分
    has_violation = len(matched) >= 2  # 同时满足2个才判定违规

    return {
        "has_violation": has_violation,
        "score_deduct": min(score_deduct, 40),  # 最多扣40
        "matched_patterns": matched,
    }


def batch_check_frames(frame_captions: List[str]) -> Dict:
    """
    批量检查多帧BLIP2描述

    Returns:
        {
            "total_violations": int,
            "max_frame_score": int,
            "total_score_deduct": int,
            "violation_frames": [{"idx": int, "caption": str, "matched": [str]}],
        }
    """
    results = [check_frame_lowbiz(cap) for cap in frame_captions]

    violation_frames = [
        {"idx": i, "caption": cap, "matched": r["matched_patterns"]}
        for i, (cap, r) in enumerate(zip(frame_captions, results))
        if r["has_violation"]
    ]

    total_deduct = sum(r["score_deduct"] for r in results)
    max_deduct = max((r["score_deduct"] for r in results), default=0)

    return {
        "total_violations": len(violation_frames),
        "max_frame_score": max_deduct,
        "total_score_deduct": min(total_deduct, 50),  # 帧检测最多扣50分
        "violation_frames": violation_frames,
    }
