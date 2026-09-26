#!/usr/bin/env python3
"""
whisper.cpp ASR Wrapper
为抖音短剧剪辑系统提供本地语音识别功能

功能:
1. 检查 whisper.cpp 是否可用
2. 调用 whisper-cli 进行语音识别
3. 解析输出，转换为标准字幕格式
4. 提供 fallback 机制
"""

import os
import sys
import subprocess
import tempfile
import re
from typing import List, Dict, Optional, Tuple

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_CLI = os.path.join(BASE_DIR, "whisper.cpp/build/bin/whisper-cli")
MODEL_PATH = os.path.join(BASE_DIR, "whisper.cpp/models/ggml-medium.bin")


def has_whisper_cpp() -> bool:
    """
    检查 whisper.cpp 是否可用
    
    Returns:
        bool: 如果 whisper-cli 和模型文件都存在，返回 True
    """
    return os.path.exists(WHISPER_CLI) and os.path.exists(MODEL_PATH)


def get_whisper_cpp_info() -> Dict:
    """
    获取 whisper.cpp 的状态信息
    
    Returns:
        Dict: 包含路径、存在性、文件大小等信息
    """
    info = {
        "whisper_cli_path": WHISPER_CLI,
        "whisper_cli_exists": os.path.exists(WHISPER_CLI),
        "model_path": MODEL_PATH,
        "model_exists": os.path.exists(MODEL_PATH),
        "model_size_mb": 0
    }
    
    if info["model_exists"]:
        size_bytes = os.path.getsize(MODEL_PATH)
        info["model_size_mb"] = round(size_bytes / (1024 * 1024), 1)
    
    return info


def parse_whisper_output(output_text: str) -> List[Dict]:
    """
    解析 whisper.cpp 的输出文本，转换为标准字幕格式
    
    Args:
        output_text: whisper-cli 的输出文本
    
    Returns:
        List[Dict]: 字幕列表，每个元素包含 start, end, text
    """
    segments = []
    
    # whisper.cpp 输出格式:
    # [00:00:00.000 --> 00:00:02.040] 這是一部短劇...
    # 或
    # 00:00:00,000 --> 00:00:02,040
    # 這是一部短劇...
    
    # 尝试匹配时间戳格式
    # 格式1: [00:00:00.000 --> 00:00:02.040]
    pattern1 = r'\[(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})\]\s*(.+)'
    
    # 格式2: 00:00:00,000 --> 00:00:02,040 (SRT 格式)
    pattern2 = r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
    
    lines = output_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 尝试匹配格式1（同一行包含时间戳和文本）
        match1 = re.match(pattern1, line)
        if match1:
            h1, m1, s1, ms1, h2, m2, s2, ms2, text = match1.groups()
            start = int(h1)*3600 + int(m1)*60 + int(s1) + int(ms1)/1000
            end = int(h2)*3600 + int(m2)*60 + int(s2) + int(ms2)/1000
            segments.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "text": text.strip()
            })
            i += 1
            continue
        
        # 尝试匹配格式2（SRT 格式，时间戳和文本分两行）
        match2 = re.match(pattern2, line)
        if match2:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = match2.groups()
            start = int(h1)*3600 + int(m1)*60 + int(s1) + int(ms1)/1000
            end = int(h2)*3600 + int(m2)*60 + int(s2) + int(ms2)/1000
            
            # 下一行是文本
            if i + 1 < len(lines):
                text = lines[i + 1].strip()
                segments.append({
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": text
                })
                i += 2
            else:
                i += 1
            continue
        
        # 如果没有匹配到时间戳，跳过此行
        i += 1
    
    # 如果没有解析到时间段，假设整个文本是一个段落
    if not segments and output_text.strip():
        # 将整个文本作为一个段落
        segments.append({
            "start": 0.0,
            "end": 0.0,
            "text": output_text.strip()
        })
    
    return segments


def transcribe_whisper_cpp(
    audio_path: str,
    language: str = "zh",
    model_size: str = "medium",
    output_format: str = "json"
) -> Optional[List[Dict]]:
    """
    使用 whisper.cpp 进行语音识别
    
    Args:
        audio_path: 音频文件路径
        language: 语言代码 (zh/en/ja/ko...)
        model_size: 模型大小 (tiny/base/small/medium/large)
        output_format: 输出格式 (json/txt/srt/vtt)
    
    Returns:
        Optional[List[Dict]]: 字幕列表，如果失败返回 None
            [{"start": float, "end": float, "text": str}, ...]
    """
    if not has_whisper_cpp():
        print("[ASR] whisper.cpp 不可用，请检查安装")
        return None
    
    if not os.path.exists(audio_path):
        print(f"[ASR] 音频文件不存在: {audio_path}")
        return None
    
    # 创建临时文件存储输出
    temp_dir = tempfile.mkdtemp()
    output_base = os.path.join(temp_dir, "whisper_output")
    
    try:
        # 构建命令
        cmd = [
            WHISPER_CLI,
            "-m", MODEL_PATH,
            "-f", audio_path,
            "-l", language,
            "-otxt" if output_format == "txt" else "-osrt",
            "-of", output_base
        ]
        
        print(f"[ASR] 开始识别: {os.path.basename(audio_path)}")
        print(f"[ASR] 命令: {' '.join(cmd[:6])}...")  # 不显示完整路径
        
        # 运行识别
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        if result.returncode != 0:
            print(f"[ASR] 识别失败，返回码: {result.returncode}")
            print(f"[ASR] stderr: {result.stderr[:500]}")
            return None
        
        # 读取识别结果
        if output_format == "txt":
            output_file = output_base + ".txt"
        else:
            output_file = output_base + ".srt"
        
        if not os.path.exists(output_file):
            print(f"[ASR] 输出文件不存在: {output_file}")
            return None
        
        with open(output_file, 'r', encoding='utf-8') as f:
            output_text = f.read()
        
        # 解析输出
        segments = parse_whisper_output(output_text)
        
        if segments:
            print(f"[ASR] 识别成功，共 {len(segments)} 个时间段")
            return segments
        else:
            print(f"[ASR] 未识别到有效内容")
            return None
    
    except subprocess.TimeoutExpired:
        print("[ASR] 识别超时（>10分钟）")
        return None
    
    except Exception as e:
        print(f"[ASR] 识别失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # 清理临时文件
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def transcribe_to_srt(audio_path: str, language: str = "zh") -> Optional[str]:
    """
    使用 whisper.cpp 进行语音识别，直接返回 SRT 格式字幕
    
    Args:
        audio_path: 音频文件路径
        language: 语言代码
    
    Returns:
        Optional[str]: SRT 格式字幕文本，如果失败返回 None
    """
    segments = transcribe_whisper_cpp(audio_path, language, output_format="srt")
    
    if not segments:
        return None
    
    # 转换为 SRT 格式
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start_str = format_time_srt(seg["start"])
        end_str = format_time_srt(seg["end"])
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_str} --> {end_str}")
        srt_lines.append(seg["text"])
        srt_lines.append("")
    
    return '\n'.join(srt_lines)


def format_time_srt(seconds: float) -> str:
    """
    将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)
    
    Args:
        seconds: 秒数
    
    Returns:
        str: SRT 时间格式字符串
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def test_asr_wrapper():
    """
    测试 ASR wrapper
    """
    print("=" * 60)
    print("测试 ASR Wrapper")
    print("=" * 60)
    
    # 检查可用性
    print("\n[1] 检查 whisper.cpp 可用性")
    info = get_whisper_cpp_info()
    print(f"  whisper-cli 存在: {info['whisper_cli_exists']}")
    print(f"  模型文件存在: {info['model_exists']}")
    print(f"  模型大小: {info['model_size_mb']} MB")
    print(f"  总体可用: {has_whisper_cpp()}")
    
    if not has_whisper_cpp():
        print("\n[错误] whisper.cpp 不可用，请先安装")
        return
    
    # 测试识别
    print("\n[2] 测试语音识别")
    test_audio = os.path.join(BASE_DIR, "output_videos/chattts_test_0.wav")
    
    if not os.path.exists(test_audio):
        print(f"\n[错误] 测试音频不存在: {test_audio}")
        print("请先运行 test_chattts_simple.py 生成测试音频")
        return
    
    segments = transcribe_whisper_cpp(test_audio, language="zh")
    
    if segments:
        print(f"\n[成功] 识别到 {len(segments)} 个时间段")
        for i, seg in enumerate(segments[:3]):
            print(f"  {i+1}. [{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text'][:50]}...")
    else:
        print("\n[失败] 识别失败")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_asr_wrapper()
