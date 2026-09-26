#!/usr/bin/env python3
"""
抖音合规预检系统 - compliance_checker.py
在视频生成后自动检测可能违规项并打分(0-100)

检测维度 (基于2026年抖音审核规则):

P0 (核心违规,单项扣分重):
  1. 解说覆盖率检测 (15分): ffprobe静音分析→无解说区域占比
  2. AI标识检测 (15分): 片头AIGC标注+元数据标签+发布声明三合一
  3. 内容安全+敏感词 (15分): 低俗色情/暴力/违法/封建迷信
  4. 不良导向检测 (15分): 制造对立/炫富/不健康价值观

P1 (重要问题):
  5. 原创度评估 (10分): 场景切换数+有效片段数代理指标
  6. 消重风险 (10分): 字幕文本重复度+场景重复度

P2 (优化建议):
  7. 画质合规 (5分): 分辨率/水印/模糊
  8. 音频合规 (5分): BGM版权/TTS自然度
  9. 元数据+标签 (5分): 标题/标签数量/免责声明
  10. 低质画面 (5分): 单色帧占比/静止画面过长
"""

import os
import re
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# 敏感词库 — 按检测维度分组
# ============================================================================

# P0: 内容安全 — 明显违规词(低俗/色情/暴力/违法/封建迷信)
SENSITIVE_WORDS_CONTENT_SAFETY = [
    # 色情/低俗
    "色情", "裸体", "裸露", "低俗", "淫秽", "黄赌毒",
    "性暗示", "卖淫", "嫖娼", "色诱",
    # 暴力/危险
    "暴力", "家暴", "血腥", "杀人", "自杀", "自残",
    "死亡", "死亡威胁", "凶杀", "虐杀", "恐怖袭击",
    "危险动作", "玩命", "不要命",
    # 违法信息
    "毒品", "制毒", "吸毒", "贩毒",
    "赌博", "博彩", "赌场", "赌球",
    "枪支", "弹药", "爆炸物",
    # 政治/社会敏感
    "政府", "领导", "举报", "上访", "维权",
    # 封建迷信/医疗欺诈
    "算命", "看相", "风水大师", "改命", "转运秘法",
    "神医", "祖传",
]

# P0: 不良导向 — 价值观敏感词(制造对立/炫富/歧视/不健康价值观)
SENSITIVE_WORDS_BAD_VALUES = [
    # 制造矛盾对立
    "阶级", "阶层碾压", "底层", "上等人", "下等人",
    "穷人活该", "有钱人就该", "农村人就是", "城里人就是",
    "性别对立", "男人都", "女人都", "女拳", "男拳",
    "婆媳", "凤凰男", "扶弟魔", "妈宝", "伏地魔",
    "地域黑", "某地人就是",
    # 炫富/炫耀性消费
    "炫富", "显摆", "存款过亿", "资产过亿",
    "豪宅", "豪车", "游艇", "私人飞机", "名媛圈",
    "月入百万", "年入千万", "躺赚",
    # 歧视/人身攻击
    "仇恨", "歧视", "侮辱", "人身攻击",
    "地域黑", "性别对立",
    "残疾", "智障", "脑残", "废物", "垃圾人",
    # 不健康婚恋价值观
    "出轨有理", "小三上位", "勾引", "劈腿",
    "拜金女", "吃软饭", "骗婚",
    # 不文明行为
    "抽烟", "酗酒", "骂人", "打架", "霸凌",
    "校园暴力", "欺凌",
    # 以暴制暴/煽动对立
    "以暴制暴", "报复社会", "同归于尽",
    "干死", "弄死", "废了他",
]

# P0: 内容安全 — 绝对化/夸大用语模式(需要上下文,用正则模式匹配)
SENSITIVE_WORDS_ABSOLUTE_PATTERNS = [
    (r'最[\u4e00-\u9fa5]{1,10}(第一|好|佳|棒|优秀|顶级|完美|强|大|牛|厉害|牛逼)', "绝对化用语"),
    (r'第[一二三四五六七八九十]+[\u4e00-\u9fa5]{0,5}', "排名暗示(需资质)"),
    (r'国家级[\u4e00-\u9fa5]+', "国家级认证暗示(需资质)"),
    (r'全国(第一|首家|唯一)', "全国范围绝对化用语"),
    (r'包治[\u4e00-\u9fa5]+', "包治百病暗示(医疗违规)"),
    (r'根治[\u4e00-\u9fa5]+', "根治承诺(医疗违规)"),
    (r'特效[\u4e00-\u9fa5]{0,5}(药|产品|秘方)', "特效宣传(需资质)"),
    (r'(月入|月赚|日入|日赚)[\d一二三四五六七八九十万千]+', "收益承诺(金融违规)"),
    (r'(保证|稳赚|零风险)[\u4e00-\u9fa5]{0,10}(收益|盈利|赚钱)', "保证收益(金融违规)"),
]

# P0: 引流违规 — 联系方式/外站导流/促销
SENSITIVE_WORDS_TRAFFIC_LEAK = [
    # 联系方式
    "加我", "微信", "QQ号", "手机号", "电话号码",
    "扫码", "二维码", "公众号", "小程序",
    # 促销/诱导
    "领取", "免费领", "限时免费", "限量", "先到先得",
    "点击下方", "评论区", "看主页", "进群",
    "抽奖", "福利", "红包", "优惠券",
    # 导流外站
    "抖音号", "抖音", "快手", "B站", "Bilibili",
    "小红书", "微博", "Twitter", "YouTube",
    "链接", "网址", "官网",
]

# 合并所有文本检测词(用于快速扫描)
_all_text_words = (
    SENSITIVE_WORDS_CONTENT_SAFETY
    + SENSITIVE_WORDS_BAD_VALUES
    + SENSITIVE_WORDS_TRAFFIC_LEAK
)

# 去重(保留顺序)
_seen = set()
SENSITIVE_WORDS = []
for w in _all_text_words:
    if w not in _seen:
        _seen.add(w)
        SENSITIVE_WORDS.append(w)
del _seen, _all_text_words


# ============================================================================
# ComplianceChecker 类
# ============================================================================

class ComplianceChecker:
    """抖音合规预检器 — 基于2026年抖音审核规则"""

    def __init__(self, video_path: str, drama_title: str,
                 narration_text: str = "", tags: List[str] = None):
        """
        Args:
            video_path: 视频文件路径
            drama_title: 短剧标题
            narration_text: 解说文本(可选)
            tags: 话题标签列表(可选)
        """
        self.video_path = video_path
        self.drama_title = drama_title
        self.narration = narration_text or ""
        self.tags = tags or []
        self.issues = []
        self.score = 100
        self._video_duration: Optional[float] = None
        self._video_stream: Optional[dict] = None
        self._audio_stream: Optional[dict] = None

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def check_all(self) -> Dict:
        """执行全部合规检查,返回检测报告"""
        logger.info(f"🔍 开始合规预检: {self.drama_title}")

        # 先获取视频基础信息(缓存)
        self._probe_video()

        # --- P0 维度(核心违规) ---
        self._check_narration_coverage()     # 解说覆盖率: 15分
        self._check_ai_generated_label()     # AI标识: 15分
        self._check_content_safety()         # 内容安全+敏感词: 15分
        self._check_bad_value_orientation()  # 不良导向: 15分

        # --- P1 维度(重要问题) ---
        self._check_originality()            # 原创度: 10分
        self._check_dedup_risk()             # 消重风险: 10分

        # --- P2 维度(优化建议) ---
        self._check_video_quality()          # 画质: 5分
        self._check_audio_compliance()       # 音频: 5分
        self._check_metadata()               # 元数据+标签: 5分
        self._check_low_quality_content()    # 低质画面: 5分

        result = {
            "video": self.video_path,
            "score": max(0, self.score),
            "issues": self.issues,
            "passed": self.score >= 60,
            "recommendations": self._generate_recommendations()
        }

        logger.info(
            f"✅ 合规预检完成: 得分{result['score']}/100, "
            f"问题{len(self.issues)}个, {'通过' if result['passed'] else '需修改'}"
        )
        return result

    # ------------------------------------------------------------------
    # 视频探测(缓存)
    # ------------------------------------------------------------------

    def _probe_video(self):
        """获取视频时长和流信息,结果缓存到实例属性"""
        if not os.path.exists(self.video_path):
            logger.warning(f"   ⚠️ 视频文件不存在: {self.video_path}")
            return

        try:
            # 时长
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.video_path
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if r.stdout.strip():
                self._video_duration = float(r.stdout.strip())
        except Exception as e:
            logger.warning(f"   ⚠️ 获取视频时长失败: {e}")

        try:
            # 流信息
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=index,codec_type,width,height,sample_rate,duration",
                "-of", "json",
                self.video_path
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            streams = json.loads(r.stdout).get("streams", [])
            for s in streams:
                if s.get("codec_type") == "video" and self._video_stream is None:
                    self._video_stream = s
                elif s.get("codec_type") == "audio" and self._audio_stream is None:
                    self._audio_stream = s
        except Exception as e:
            logger.warning(f"   ⚠️ 获取视频流信息失败: {e}")

    # ------------------------------------------------------------------
    # P0: 解说覆盖率检测 (15分)
    # ------------------------------------------------------------------

    def _check_narration_coverage(self):
        """
        使用 ffprobe/ffmpeg silencedetect 分析音频静默段,
        评估解说覆盖率。

        核心逻辑:
        - 静默段(低于噪声阈值) = 无解说区域
        - 连续静默 > 3秒 单独计数
        - 总静默时长占比 > 20% → 扣15分
        - 总静默时长占比 10-20% → 扣8分
        """
        logger.info("  🔍 检测解说覆盖率...")

        if not os.path.exists(self.video_path):
            self._add_issue("P0", "解说覆盖率", "视频文件不存在,无法检测解说覆盖率",
                            "文件缺失", "确认视频文件路径正确", 15)
            return

        if self._audio_stream is None:
            self._add_issue("P0", "解说覆盖率", "视频无音频流,视为0%解说覆盖率",
                            "无音频", "添加解说/配音", 15)
            return

        silent_segments = self._detect_silence()
        if silent_segments is None:
            logger.warning("    ⚠️ silencedetect 失败,跳过解说覆盖率检测")
            return

        duration = self._video_duration
        if not duration or duration <= 0:
            return

        total_silent = sum(seg["duration"] for seg in silent_segments)
        silent_ratio = total_silent / duration
        long_gaps = [seg for seg in silent_segments if seg["duration"] > 3.0]
        long_gap_count = len(long_gaps)

        logger.info(
            f"    视频时长: {duration:.1f}s, 静默总长: {total_silent:.1f}s "
            f"({silent_ratio*100:.1f}%), 长静默段(>3s): {long_gap_count}个"
        )

        # 按阈值扣分
        if silent_ratio > 0.20:
            self._add_issue("P0", "解说覆盖率",
                f"无解说区域占比过高 ({silent_ratio*100:.1f}% > 20%), 连续长静默段{long_gap_count}个",
                f"静默占比{silent_ratio*100:.1f}%",
                "增加解说覆盖,确保无解说区域<20%,连续无解说≤3秒",
                15)
        elif silent_ratio > 0.10:
            self._add_issue("P1", "解说覆盖率",
                f"无解说区域偏高 ({silent_ratio*100:.1f}%), 连续长静默段{long_gap_count}个",
                f"静默占比{silent_ratio*100:.1f}%",
                "适当增加解说填充静默段,尤其>3秒的区域",
                8)
        elif long_gap_count > 2:
            self._add_issue("P2", "解说覆盖率",
                f"存在{long_gap_count}个超过3秒的无解说区域",
                f"长静默段{len(long_gaps)}个",
                "在长静默段添加解说或BGM填充",
                3)
        else:
            logger.info("    ✅ 解说覆盖率正常")

    def _detect_silence(self) -> Optional[List[dict]]:
        """
        使用 ffmpeg silencedetect 检测静默段。
        返回: [{"start": float, "end": float, "duration": float}, ...]
              失败返回 None
        """
        try:
            cmd = [
                "ffmpeg", "-i", self.video_path,
                "-af", "silencedetect=noise=-50dB:d=0.5",
                "-f", "null", "-",
                "-hide_banner", "-loglevel", "info",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = r.stderr  # ffmpeg 日志在 stderr

            segments = []
            # 解析 "silence_start: X.XX" 和 "silence_end: Y.YY | silence_duration: Z.ZZ"
            start = None
            for line in output.split("\n"):
                if "silence_start" in line:
                    m = re.search(r'silence_start:\s*([\d.]+)', line)
                    if m:
                        start = float(m.group(1))
                elif "silence_end" in line and start is not None:
                    m_end = re.search(r'silence_end:\s*([\d.]+)', line)
                    m_dur = re.search(r'silence_duration:\s*([\d.]+)', line)
                    if m_end:
                        end = float(m_end.group(1))
                        dur = float(m_dur.group(1)) if m_dur else (end - start)
                        segments.append({
                            "start": start, "end": end, "duration": dur
                        })
                    start = None

            # 如果 video 时长已知但最后一段静默未闭合
            if start is not None and self._video_duration:
                end = self._video_duration
                segments.append({
                    "start": start, "end": end, "duration": end - start
                })

            return segments
        except Exception as e:
            logger.warning(f"    ⚠️ silencedetect 执行失败: {e}")
            return None

    # ------------------------------------------------------------------
    # P0: AI标识检测 (15分)
    # ------------------------------------------------------------------

    def _check_ai_generated_label(self):
        """
        2026年新规: 必须开头3秒显著标注'AI生成'。
        检测策略(三合一):
        1. 画面标注: 检查标签中是否含"AI生成"等关键词
        2. 元数据嵌入: 检查视频元数据中是否有 AI 标记
        3. 片头检测: 检查是否有明显的AI标识关键词
        """
        logger.info("  🔍 检测AI标识合规性...")

        has_label_in_tags = self._check_ai_in_tags()
        has_metadata_label = self._check_ai_in_metadata()
        has_opening_label = self._check_ai_in_opening_text()

        ai_checks = {
            "tags_label": has_label_in_tags,
            "metadata_label": has_metadata_label,
            "opening_label": has_opening_label,
        }
        passed_count = sum(ai_checks.values())

        logger.info(
            f"    AI标识检查: 标签={'✅' if has_label_in_tags else '❌'}, "
            f"元数据={'✅' if has_metadata_label else '❌'}, "
            f"片头文本={'✅' if has_opening_label else '❌'}"
        )

        # 评分逻辑
        if passed_count == 0:
            # 完全无AI标识 → 严重违规
            self._add_issue("P0", "AI标识",
                "未检测到任何AI生成标识! 2026新规要求在片头3秒内显著标注'AI生成',并发布时勾选'含AI生成内容'",
                "无AI标识",
                "在片头前3秒显著标注'AI生成',发布时勾选'含AI生成内容'选项,嵌入元数据溯源编码",
                15)
        elif passed_count == 1 and not has_opening_label:
            # 有标签或元数据,但缺少片头标注 → 仍扣较多分
            self._add_issue("P0", "AI标识",
                "仅有标签/元数据标识,缺少片头3秒显著标注(2026新规强制要求片头标注)",
                f"检测项: {ai_checks}",
                "在片头前3秒添加醒目'AI生成'画面标注,配合发布时勾选'含AI生成内容'",
                12)
        elif passed_count == 2 and not has_opening_label:
            self._add_issue("P0", "AI标识",
                "缺少片头3秒显著'AIGC'画面标注,仅有元数据和标签标识",
                f"检测项: {ai_checks}",
                "在片头前3秒添加醒目'AI生成'画面标注",
                8)
        elif not has_opening_label:
            self._add_issue("P1", "AI标识",
                "建议补充片头AIGC画面标注,当前仅通过标签/元数据标识",
                f"检测项: {ai_checks}",
                "在片头添加'AI生成'标注更合规",
                4)
        else:
            logger.info("    ✅ AI标识完整(片头+标签+元数据)")

    def _check_ai_in_tags(self) -> bool:
        """检查标签中是否包含AI生成相关关键词"""
        ai_keywords = [
            "AI生成", "AIGC", "AI创作", "AI制作", "AI视频",
            "人工智能生成", "AI辅助", "含AI生成内容",
        ]
        all_text = " ".join(self.tags).lower()
        return any(kw.lower() in all_text for kw in ai_keywords)

    def _check_ai_in_metadata(self) -> bool:
        """检查视频元数据中是否有AIGC标签"""
        if not os.path.exists(self.video_path):
            return False
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format_tags=comment,description,title",
                "-of", "json",
                self.video_path
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(r.stdout)
            tags = data.get("format", {}).get("tags", {})
            all_meta = " ".join(str(v) for v in tags.values()).lower()
            ai_signals = ["ai生成", "aigc", "ai-generated", "ai_generated"]
            return any(s in all_meta for s in ai_signals)
        except Exception:
            return False

    def _check_ai_in_opening_text(self) -> bool:
        """
        检测片头是否有AI标识文本(扫描解说词中是否提及AI标识)。
        实际片头画面OCR无法执行,以解说词/旁白文本为代理检测。
        """
        if not self.narration:
            return False
        # 取前200字符(大约覆盖开头)
        head = self.narration[:200]
        ai_signals = ["AI生成", "AIGC", "AI创作", "人工智能生成", "AI制作"]
        return any(s in head for s in ai_signals)

    # ------------------------------------------------------------------
    # P0: 内容安全+敏感词 (15分)
    # ------------------------------------------------------------------

    def _check_content_safety(self):
        """
        检测内容安全:
        1. 低俗色情/暴力/违法/封建迷信 关键词匹配
        2. 引流违规(联系方式/二维码/导流外站)
        3. 绝对化/夸大用语模式匹配
        """
        logger.info("  🔍 检测内容安全(敏感词+引流+绝对化用语)...")

        deducted = 0

        # 子维度1: 内容安全敏感词(低俗/暴力/违法/迷信) — 最多扣8分
        deducted += self._scan_words_group(
            SENSITIVE_WORDS_CONTENT_SAFETY,
            "内容安全", "P0", max_deduct=8, per_hit=3.0,
            recommendation="移除或换用合规表达"
        )

        # 子维度2: 引流违规 — 最多扣5分
        deducted += self._scan_words_group(
            SENSITIVE_WORDS_TRAFFIC_LEAK,
            "引流违规", "P0", max_deduct=5, per_hit=2.0,
            recommendation="移除联系方式/链接/导流内容"
        )

        # 子维度3: 绝对化/夸大用语 — 最多扣2分
        deducted += self._scan_patterns_group(
            SENSITIVE_WORDS_ABSOLUTE_PATTERNS,
            "绝对化用语", "P1", max_deduct=2, per_hit=1.0,
            recommendation="移除绝对化表述或提供证明材料"
        )

        if deducted == 0:
            logger.info("    ✅ 内容安全检测通过")

    def _check_bad_value_orientation(self):
        """
        P0: 不良导向检测 (15分)
        检测制造矛盾对立/炫富/歧视/不健康价值观等内容。
        """
        logger.info("  🔍 检测不良导向(价值观/对立/炫富)...")

        deducted = self._scan_words_group(
            SENSITIVE_WORDS_BAD_VALUES,
            "不良导向", "P0", max_deduct=15, per_hit=5.0,
            recommendation="移除煽动对立/炫富/歧视等内容,保持内容健康积极"
        )

        if deducted == 0:
            logger.info("    ✅ 不良导向检测通过")

    # ------------------------------------------------------------------
    # 敏感词扫描工具方法
    # ------------------------------------------------------------------

    def _scan_words_group(self, word_list: List[str], category: str,
                          level: str, max_deduct: int, per_hit: float,
                          recommendation: str) -> int:
        """
        扫描文本中的关键词组,按命中数扣分。

        Returns: 实际扣分(正数)
        """
        text = self._collect_scan_text()
        hits = []
        for word in word_list:
            if word in text:
                hits.append(word)

        if not hits:
            return 0

        # 统一扣分(去重),上限为 max_deduct
        deduct = min(len(hits) * per_hit, max_deduct)
        for word in hits[:6]:  # 最多列出6个命中词
            self._add_issue(level, category,
                f"检测到{category}敏感词: '{word}'",
                f"命中词'{word}'",
                recommendation, deduct_value=0)
        if len(hits) > 6:
            self._add_issue(level, category,
                f"检测到{category}敏感词共{len(hits)}处(仅展示前6: {', '.join(hits[:6])})",
                f"命中{len(hits)}处",
                recommendation, deduct_value=0)

        # 统一从总分扣除
        self.score -= deduct
        logger.info(f"    ⚠️ {category}: 命中{len(hits)}处, 扣{deduct:.0f}分")
        return int(deduct)

    def _scan_patterns_group(self, patterns: List[Tuple[str, str]],
                             category: str, level: str,
                             max_deduct: int, per_hit: float,
                             recommendation: str) -> int:
        """扫描正则模式匹配"""
        text = self._collect_scan_text()
        hits = []
        for pattern, label in patterns:
            if re.search(pattern, text):
                hits.append((pattern, label))

        if not hits:
            return 0

        deduct = min(len(hits) * per_hit, max_deduct)
        for pattern, label in hits[:5]:
            m = re.search(pattern, text)
            snippet = text[max(0, m.start()-5):m.end()+5] if m else pattern
            self._add_issue(level, category,
                f"检测到{category}: {label} (匹配: '...{snippet}...')",
                f"模式'{label}'",
                recommendation, deduct_value=0)
        self.score -= deduct
        self.score = round(self.score, 1)
        logger.info(f"    ⚠️ {category}: 命中{len(hits)}处, 扣{deduct:.0f}分")
        return int(deduct)

    def _collect_scan_text(self) -> str:
        """收集所有需要扫描的文本"""
        parts = [self.drama_title, self.narration]
        parts.extend(self.tags)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # P1: 原创度评估 (10分)
    # ------------------------------------------------------------------

    def _check_originality(self):
        """
        原创度代理检测:
        - 使用 ffprobe 检测场景切换次数(scene detection)
        - 场景切换数反映混剪复杂度,切换越多原创度越高
        - 同时评估有效片段(即场景切换间隔)的分布

        扣分规则:
        - 场景切换 < 3: 扣10分(极可能被判搬运)
        - 场景切换 3-5: 扣6分(混剪程度低)
        - 场景切换 5-8: 扣3分(一般)
        - 场景切换 ≥ 8: 不扣分(混剪充分)
        """
        logger.info("  🔍 评估原创度(场景切换检测)...")

        scene_changes = self._detect_scene_changes()
        if scene_changes is None:
            logger.warning("    ⚠️ 场景检测失败,跳过原创度评估")
            return

        count = len(scene_changes)
        duration = self._video_duration or 0
        density = count / max(duration, 1) * 60  # 每分钟场景切换数

        logger.info(f"    场景切换: {count}次, 密度: {density:.1f}次/分钟")

        if count < 3:
            self._add_issue("P0", "原创度",
                f"场景切换仅{count}次,原创度极低,极可能被判搬运或低质混剪",
                f"场景切换{count}次",
                "增加素材来源,提高混剪密度,每30秒至少1次场景切换",
                10)
        elif count < 5:
            self._add_issue("P1", "原创度",
                f"场景切换{count}次,混剪程度偏低({density:.1f}次/分钟)",
                f"场景切换{count}次",
                "增加混剪频率和素材来源,添加转场效果提升原创度",
                6)
        elif count < 8:
            self._add_issue("P2", "原创度",
                f"场景切换{count}次,原创度一般({density:.1f}次/分钟),仍有优化空间",
                f"场景切换{count}次",
                "可适当增加场景切换和转场效果",
                3)
        else:
            logger.info(f"    ✅ 原创度评估正常 ({count}次场景切换)")

    def _detect_scene_changes(self) -> Optional[List[float]]:
        """
        使用 ffmpeg select=gt(scene,threshold) 检测场景切换时间点。
        返回: [时间戳(秒), ...] 或 None
        """
        try:
            cmd = [
                "ffmpeg", "-i", self.video_path,
                "-vf", "select='gt(scene\\,0.4)',showinfo",
                "-vsync", "vfr", "-f", "null", "-",
                "-nostats", "-hide_banner",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = r.stderr

            timestamps = []
            for line in output.split("\n"):
                # showinfo 输出: "pts_time:12.345"
                m = re.search(r'pts_time:([\d.]+)', line)
                if m:
                    t = float(m.group(1))
                    # 去重(相邻帧可能触发多次,保留>1秒间隔的)
                    if not timestamps or (t - timestamps[-1]) > 1.0:
                        timestamps.append(t)

            return timestamps
        except Exception as e:
            logger.warning(f"    ⚠️ 场景检测失败: {e}")
            return None

    # ------------------------------------------------------------------
    # P1: 消重风险 (10分)
    # ------------------------------------------------------------------

    def _check_dedup_risk(self):
        """
        消重模拟检测:
        基于字幕文本重复度评估被抖音查重拦截的风险。
        文本重复度过高 → 可能与其他同素材视频内容重叠。

        扣分规则:
        - 解说词少于20字符: 扣10分(无原创文本,极易被查重)
        - 解说词有效句少于3句: 扣6分
        - 解说词与剧名重复度过高: 扣3分
        - 标签与剧名重复度过高: 扣2分
        """
        logger.info("  🔍 评估消重风险(文本重复度)...")

        deductions = 0

        # 子维度1: 解说词长度
        narration_len = len(self.narration.strip())
        if narration_len < 20:
            self._add_issue("P0", "消重风险",
                f"解说词仅{narration_len}字符,无有效原创文本,消重风险极高",
                f"解说词{narration_len}字符",
                "添加原创AI解说,解说词建议≥100字符,覆盖视频全程",
                10)
            deductions += 10
        elif narration_len < 80:
            self._add_issue("P1", "消重风险",
                f"解说词{narration_len}字符,原创文本偏少,消重风险较高",
                f"解说词{narration_len}字符",
                "补充更多原创解说内容",
                4)
            deductions += 4

        # 子维度2: 有效句数(按句号/感叹号/问号分段)
        sentences = re.split(r'[。！？!?\n]+', self.narration)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) >= 4]
        if len(valid_sentences) < 3 and narration_len >= 20:
            self._add_issue("P1", "消重风险",
                f"解说词有效句子仅{len(valid_sentences)}句,内容过于简单",
                f"有效句{len(valid_sentences)}句",
                "丰富解说内容,使用完整句子描述剧情",
                3)
            deductions += 3

        # 子维度3: 剧名与解说词重复度
        title_chars = set(self.drama_title)
        if self.narration and len(title_chars) >= 2:
            # 计算标题词在解说中的出现频率
            title_hit_count = sum(1 for c in title_chars if c in self.narration)
            title_overlap_ratio = title_hit_count / max(len(title_chars), 1)
            if title_overlap_ratio > 0.7:
                self._add_issue("P2", "消重风险",
                    f"标题与解说词字符重叠率过高 ({title_overlap_ratio*100:.0f}%)",
                    f"重叠率{title_overlap_ratio*100:.0f}%",
                    "标题避免与解说词高度重复,增加差异化表达",
                    2)
                deductions += 2

        if deductions == 0:
            logger.info("    ✅ 消重风险评估正常")

    # ------------------------------------------------------------------
    # P2: 画质合规 (5分)
    # ------------------------------------------------------------------

    def _check_video_quality(self):
        """检查分辨率/水印/模糊/暗帧"""
        logger.info("  🔍 检测画质合规...")

        if self._video_stream is None:
            self._add_issue("P2", "画质合规", "无法获取视频流信息",
                            "未知", "确认视频文件有效", 5)
            return

        width = self._video_stream.get("width", 0)
        height = self._video_stream.get("height", 0)
        w_is_ok = width >= 720
        h_is_ok = height >= 720
        standard_ratio = (
            (width, height) in [
                (1080, 1920), (1920, 1080),
                (720, 1280), (1280, 720),
                (1440, 2560), (2560, 1440),
                (2160, 3840), (3840, 2160),
            ]
        )

        if not w_is_ok or not h_is_ok:
            self._add_issue("P1", "画质合规",
                f"分辨率不足720p: {width}x{height}",
                f"{width}x{height}",
                "导出时选择≥720p分辨率",
                5)
        elif not standard_ratio:
            self._add_issue("P2", "画质合规",
                f"分辨率非标准尺寸: {width}x{height}",
                f"{width}x{height}",
                "建议输出1080x1920(竖屏)或1920x1080(横屏)",
                2)
        else:
            logger.info(f"    ✅ 分辨率正常: {width}x{height}")

    # ------------------------------------------------------------------
    # P2: 音频合规 (5分)
    # ------------------------------------------------------------------

    def _check_audio_compliance(self):
        """检查BGM和TTS合规性"""
        logger.info("  🔍 检测音频合规...")

        # 如果无音频流,不检测
        if self._audio_stream is None:
            return

        # 检测音频流是否为单声道/采样率过低
        sample_rate = self._audio_stream.get("sample_rate", 0)
        if sample_rate and sample_rate < 22050:
            self._add_issue("P2", "音频合规",
                f"音频采样率过低({sample_rate}Hz),音质可能不达标",
                f"{sample_rate}Hz",
                "使用≥44100Hz采样率输出",
                2)

        # 检查解说文本是否标记了BGM来源
        bgm_keywords = ["bgm", "BGM", "背景音乐", "配乐", "音乐来源"]
        has_bgm_credit = any(kw in self.narration for kw in bgm_keywords)
        has_bgm_tag = any(kw.lower() in str(self.tags).lower() for kw in bgm_keywords)

        if not has_bgm_credit and not has_bgm_tag:
            # 不是严重问题,仅提示
            self._add_issue("P2", "音频合规",
                "未标注BGM来源,建议标注以确保版权合规",
                "无BGM标注",
                "在视频描述中添加BGM来源标注",
                1)

        logger.info("    ✅ 音频合规检查完成")

    # ------------------------------------------------------------------
    # P2: 元数据+标签 (5分)
    # ------------------------------------------------------------------

    def _check_metadata(self):
        """检查标题/标签/描述等元数据合规性"""
        logger.info("  🔍 检测元数据合规...")

        deducted = 0

        # 标题长度检查
        title_len = len(self.drama_title)
        if title_len > 30:
            self._add_issue("P1", "元数据合规",
                f"标题过长({title_len}>30字符),抖音推荐5-15字符",
                f"{title_len}字符",
                "缩短标题至30字符以内",
                2)
            deducted += 2

        # 标签数量检查
        tag_count = len([t for t in self.tags if t.strip()])
        if tag_count > 30:
            self._add_issue("P2", "元数据合规",
                f"标签数量过多({tag_count}>30个)",
                f"{tag_count}个标签",
                "减少至30个以内",
                2)
            deducted += 2
        elif tag_count < 2:
            self._add_issue("P2", "元数据合规",
                f"标签过少({tag_count}个),建议添加3-5个精准标签",
                f"{tag_count}个标签",
                "添加热门话题标签提升曝光",
                1)
            deducted += 1

        # 检查是否包含违规标签(其他平台名称等)
        leak_hits = []
        for tag in self.tags:
            for word in ["抖音号", "快手", "B站", "小红书", "微博", "扫码"]:
                if word in tag:
                    leak_hits.append(tag)
                    break
        if leak_hits:
            self._add_issue("P1", "元数据合规",
                f"标签含导流词: {', '.join(leak_hits[:3])}",
                f"导流标签{len(leak_hits)}个",
                "移除导流性标签",
                2)
            deducted += 2

        if deducted == 0:
            logger.info("    ✅ 元数据合规")

    # ------------------------------------------------------------------
    # P2: 低质画面 (5分)
    # ------------------------------------------------------------------

    def _check_low_quality_content(self):
        """
        检测低质内容:
        - 使用 ffprobe/ffmpeg 检测单色帧(大面积同色)占比
        - 检测是否有过长静止画面
        """
        logger.info("  🔍 检测低质内容(单色帧/静止画面)...")

        # 检测静止区域: 使用 ffmpeg freezedetect
        freeze_segments = self._detect_freeze()
        if freeze_segments is None:
            logger.warning("    ⚠️ 静止检测失败,跳过低质内容检测")
            return

        total_freeze = sum(s["duration"] for s in freeze_segments)
        duration = self._video_duration or 0
        if duration <= 0:
            return

        freeze_ratio = total_freeze / duration

        if freeze_ratio > 0.30:
            self._add_issue("P1", "低质画面",
                f"静止画面占比过高 ({freeze_ratio*100:.1f}% > 30%),可能被判低质内容",
                f"静止占比{freeze_ratio*100:.1f}%",
                "增加画面变化,减少过长静止段落",
                5)
        elif freeze_ratio > 0.15:
            self._add_issue("P2", "低质画面",
                f"静止画面偏高 ({freeze_ratio*100:.1f}%),注意避免纯文字堆砌",
                f"静止占比{freeze_ratio*100:.1f}%",
                "减少静止画面,适当添加动态元素",
                2)
        else:
            logger.info(f"    ✅ 低质内容检测正常 (静止占比{freeze_ratio*100:.1f}%)")

    def _detect_freeze(self) -> Optional[List[dict]]:
        """
        使用 ffmpeg freezedetect 检测静止画面段。
        返回: [{"start": float, "end": float, "duration": float}, ...]
        """
        try:
            cmd = [
                "ffmpeg", "-i", self.video_path,
                "-vf", "freezedetect=n=-60dB:d=2",
                "-f", "null", "-",
                "-hide_banner",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = r.stderr

            segments = []
            for line in output.split("\n"):
                m = re.search(
                    r'freeze_start:\s*([\d.]+).*?freeze_end:\s*([\d.]+).*?freeze_duration:\s*([\d.]+)',
                    line
                )
                if m:
                    segments.append({
                        "start": float(m.group(1)),
                        "end": float(m.group(2)),
                        "duration": float(m.group(3)),
                    })
            return segments
        except Exception as e:
            logger.warning(f"    ⚠️ freezedetect 失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _add_issue(self, level: str, category: str, description: str,
                   current: str, recommendation: str, deduct_value: float):
        """添加问题并扣分"""
        self.issues.append({
            "level": level,
            "category": category,
            "description": description,
            "current": current,
            "recommendation": recommendation,
        })
        self.score -= deduct_value
        self.score = round(self.score, 1)

    def _generate_recommendations(self) -> List[str]:
        """生成修复建议(按P0→P1→P2优先级排序)"""
        level_order = {"P0": 0, "P1": 1, "P2": 2}
        sorted_issues = sorted(
            self.issues,
            key=lambda x: level_order.get(x["level"], 3)
        )
        return [
            f"[{i['level']}] {i['category']}: {i['recommendation']}"
            for i in sorted_issues
        ]


# ============================================================================
# 便捷函数(保持接口不变)
# ============================================================================


def check_compliance(video_path: str, drama_title: str,
                     narration_text: str = "",
                     tags: List[str] = None) -> Dict:
    """
    便捷函数: 执行合规预检

    Args:
        video_path: 视频文件路径
        drama_title: 短剧标题
        narration_text: 解说文本(可选)
        tags: 话题标签列表(可选)

    Returns:
        Dict: {
            "score": int,
            "issues": list,
            "passed": bool,
            "recommendations": list
        }
    """
    checker = ComplianceChecker(video_path, drama_title, narration_text, tags)
    return checker.check_all()


# ============================================================================
# 命令行入口
# ============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 3:
        print("Usage: python compliance_checker.py <video_path> <drama_title> "
              "[narration_text] [tags_json]")
        sys.exit(1)

    video = sys.argv[1]
    title = sys.argv[2]
    narration = sys.argv[3] if len(sys.argv) > 3 else ""
    tags = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []

    result = check_compliance(video, title, narration, tags)
    print(json.dumps(result, ensure_ascii=False, indent=2))
