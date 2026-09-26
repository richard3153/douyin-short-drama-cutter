#!/usr/bin/env python3
"""
ChatTTS TTS Wrapper - 正确实现
为 ai_short_video_cutter_pro.py 提供 ChatTTS 离线 TTS 功能
"""

import os
import sys
import tempfile
import time
import warnings

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(WORK_DIR, "models", "ChatTTS")

def has_chattts():
    """检查 ChatTTS 是否可用"""
    try:
        import ChatTTS
        return True
    except ImportError:
        return False

def _init_chattts():
    """初始化 ChatTTS（延迟初始化）"""
    if not hasattr(_init_chattts, '_chat_instance'):
        _init_chattts._chat_instance = None
        _init_chattts._initialized = False
        
        try:
            import ChatTTS
            chat = ChatTTS.Chat()
            
            # 加载模型
            if os.path.exists(MODEL_DIR):
                print(f"[ChatTTS] 加载本地模型: {MODEL_DIR}")
                chat.load(custom_path=MODEL_DIR, compile=False)
            else:
                print("[ChatTTS] 加载在线模型...")
                chat.download_models(source='huggingface')
            
            _init_chattts._chat_instance = chat
            _init_chattts._initialized = True
            print("[ChatTTS] 初始化成功")
        except Exception as e:
            print(f"[ChatTTS] 初始化失败: {e}")
    
    return _init_chattts._chat_instance

def tts_chattts(text: str, output_path: str = None, seed: int = None) -> str:
    """
    ChatTTS 语音合成

    Args:
        text: 要合成的文本
        output_path: 输出音频文件路径（可选，默认自动生成）
        seed: 随机种子（固定则每次生成相同音色）

    Returns:
        成功时返回音频文件路径，失败时返回 None
    """
    if not has_chattts():
        print("[ChatTTS] 未安装，请运行: pip install chattts")
        return None

    chat = _init_chattts()
    if chat is None:
        print("[ChatTTS] 初始化失败，无法合成")
        return None

    try:
        import torch
        import torchaudio

        # 确定输出路径
        if output_path is None:
            output_path = os.path.join(WORK_DIR, "output_videos", f"tts_chattts_{int(time.time())}.wav")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 固定随机种子，确保音色一致
        if seed is not None:
            torch.manual_seed(seed)

        # 生成音频
        start_time = time.time()
        texts = [text]
        wavs = chat.infer(
            texts,
            use_decoder=True,
            split_text=False
        )
        elapsed = time.time() - start_time

        # 保存音频 (ChatTTS 默认采样率 24000)
        wav = wavs[0] if isinstance(wavs, list) else wavs
        if not isinstance(wav, torch.Tensor):
            wav = torch.from_numpy(wav)
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)

        torchaudio.save(output_path, wav, 24000)

        print(f"[ChatTTS] 合成成功: {output_path} (耗时 {elapsed:.2f}秒)")
        return output_path

    except Exception as e:
        print(f"[ChatTTS] 合成失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def tts_chattts_batch(texts: list, output_dir: str = None, seed: int = None) -> list:
    """
    ChatTTS 批量语音合成 - 所有文本一次性生成，确保音色一致
    
    Args:
        texts: 文本列表
        output_dir: 输出目录
        seed: 随机种子(固定则每次生成相同音色)
    
    Returns:
        成功时返回音频文件路径列表，全部失败返回空列表
    """
    if not texts:
        return []
    if not has_chattts():
        print("[ChatTTS] 未安装")
        return []
    
    chat = _init_chattts()
    if chat is None:
        print("[ChatTTS] 初始化失败")
        return []
    
    try:
        import torch
        import torchaudio
        import time as _time

        if output_dir is None:
            output_dir = os.path.join(WORK_DIR, "output_videos")
        os.makedirs(output_dir, exist_ok=True)

        if seed is not None:
            torch.manual_seed(seed)

        start_time = _time.time()
        
        # 一次 infer() 传入所有文本 → 统一音色
        wavs = chat.infer(
            texts,
            use_decoder=True,
            split_text=False
        )
        elapsed = _time.time() - start_time

        if not wavs:
            return []
        if not isinstance(wavs, (list, tuple)):
            wavs = [wavs]

        result_paths = []
        for i, wav in enumerate(wavs):
            timestamp = int(_time.time())
            output_path = os.path.join(output_dir, f"tts_chunk_{timestamp}_{i}.wav")
            
            if not isinstance(wav, torch.Tensor):
                wav = torch.from_numpy(wav)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            
            torchaudio.save(output_path, wav, 24000)
            result_paths.append(output_path)

        print(f"[ChatTTS] 批量合成成功: {len(result_paths)}个片段 (耗时 {elapsed:.2f}秒)")
        return result_paths

    except Exception as e:
        print(f"[ChatTTS] 批量合成失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def tts_chattts_with_fallback(text: str, voice: str = None, output_path: str = None) -> str:
    """
    ChatTTS TTS with fallback to other methods
    
    优先级: ChatTTS → edge-tts → macOS say
    """
    # 尝试 ChatTTS
    result = tts_chattts(text, output_path)
    if result:
        return result
    
    # Fallback to other methods (需要在主文件中实现)
    print("[ChatTTS] ChatTTS 失败，将使用 fallback 方法")
    return None

if __name__ == "__main__":
    # 测试
    print("测试 ChatTTS TTS...")
    result = tts_chattts("你好，这是一个测试。短剧解说配音效果测试。")
    if result:
        print(f"成功! 输出文件: {result}")
    else:
        print("失败!")
