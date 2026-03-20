#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sherpa-ONNX 关键词检测 Demo

使用 PyAudio 从麦克风实时读取音频，结合 sherpa-onnx 进行关键词检测 (KWS)。
当检测到预定义的关键词时，打印日志信息。

参考: https://github.com/k2-fsa/sherpa-onnx
模型下载: https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html

用法示例（中文模型）:
    python3 kws_demo.py \
        --tokens ./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/tokens.txt \
        --encoder ./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/encoder-epoch-12-avg-2-chunk-16-left-64.onnx \
        --decoder ./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/decoder-epoch-12-avg-2-chunk-16-left-64.onnx \
        --joiner ./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/joiner-epoch-12-avg-2-chunk-16-left-64.onnx \
        --keywords-file ./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/test_wavs/test_keywords.txt
"""

import argparse
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

import numpy as np

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 检查并导入 pyaudio
try:
    import pyaudio
except ImportError:
    logger.error("请先安装 pyaudio: pip3 install pyaudio")
    sys.exit(1)

# 检查并导入 sherpa_onnx
try:
    import sherpa_onnx
except ImportError:
    logger.error("请先安装 sherpa-onnx: pip3 install sherpa-onnx")
    sys.exit(1)


def check_file_exists(filepath: str, description: str = "文件") -> bool:
    """检查文件是否存在"""
    if not Path(filepath).is_file():
        logger.error(f"{description}不存在: {filepath}")
        return False
    return True


def get_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Sherpa-ONNX 关键词检测 Demo - 使用 PyAudio 从麦克风实时检测关键词",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 模型文件参数
    parser.add_argument(
        "--tokens",
        type=str,
        required=True,
        help="tokens.txt 文件路径"
    )
    parser.add_argument(
        "--encoder",
        type=str,
        required=True,
        help="编码器 ONNX 模型路径"
    )
    parser.add_argument(
        "--decoder",
        type=str,
        required=True,
        help="解码器 ONNX 模型路径"
    )
    parser.add_argument(
        "--joiner",
        type=str,
        required=True,
        help="joiner ONNX 模型路径"
    )
    parser.add_argument(
        "--keywords-file",
        type=str,
        required=True,
        help="关键词文件路径，每行一个关键词（需要先用 text2token 工具处理）"
    )

    # 推理参数
    parser.add_argument(
        "--num-threads",
        type=int,
        default=2,
        help="神经网络推理使用的线程数"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="cpu",
        choices=["cpu", "cuda", "coreml"],
        help="推理后端: cpu, cuda, coreml"
    )
    parser.add_argument(
        "--max-active-paths",
        type=int,
        default=4,
        help="解码时保留的最大活跃路径数"
    )
    parser.add_argument(
        "--num-trailing-blanks",
        type=int,
        default=1,
        help="关键词后跟随的空白帧数（如果关键词之间有重叠token，可设置为较大值如8）"
    )
    parser.add_argument(
        "--keywords-score",
        type=float,
        default=1.0,
        help="关键词 token 的增强分数，越大越容易被检测到"
    )
    parser.add_argument(
        "--keywords-threshold",
        type=float,
        default=0.25,
        help="关键词触发阈值（概率），越大越难触发"
    )

    # 音频参数
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="音频采样率（Hz）"
    )
    parser.add_argument(
        "--chunk-duration",
        type=float,
        default=0.1,
        help="每次读取的音频时长（秒）"
    )

    return parser.parse_args()


def list_audio_devices():
    """列出所有可用的音频输入设备"""
    p = pyaudio.PyAudio()
    logger.info("可用的音频输入设备:")
    
    default_input_device = p.get_default_input_device_info()
    logger.info(f"  默认输入设备 ID: {default_input_device['index']}, 名称: {default_input_device['name']}")
    
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['maxInputChannels'] > 0:  # 只显示有输入通道的设备
            logger.info(f"  设备 ID: {i}, 名称: {dev_info['name']}, 输入通道数: {dev_info['maxInputChannels']}")
    
    p.terminate()
    return default_input_device['index']


def create_keyword_spotter(args) -> sherpa_onnx.KeywordSpotter:
    """创建关键词检测器"""
    logger.info("正在初始化关键词检测器...")
    
    kws = sherpa_onnx.KeywordSpotter(
        tokens=args.tokens,
        encoder=args.encoder,
        decoder=args.decoder,
        joiner=args.joiner,
        num_threads=args.num_threads,
        max_active_paths=args.max_active_paths,
        keywords_file=args.keywords_file,
        keywords_score=args.keywords_score,
        keywords_threshold=args.keywords_threshold,
        num_trailing_blanks=args.num_trailing_blanks,
        provider=args.provider,
    )
    
    logger.info("关键词检测器初始化完成！")
    return kws


def main():
    """主函数"""
    args = get_args()
    
    # 检查所有必需文件是否存在
    files_ok = True
    files_ok &= check_file_exists(args.tokens, "tokens 文件")
    files_ok &= check_file_exists(args.encoder, "encoder 模型")
    files_ok &= check_file_exists(args.decoder, "decoder 模型")
    files_ok &= check_file_exists(args.joiner, "joiner 模型")
    files_ok &= check_file_exists(args.keywords_file, "关键词文件")
    
    if not files_ok:
        logger.error("请检查模型文件路径是否正确！")
        logger.error("模型下载地址: https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html")
        sys.exit(1)
    
    # 列出音频设备
    default_device_id = list_audio_devices()
    
    # 创建关键词检测器
    kws = create_keyword_spotter(args)
    
    # 创建 stream
    stream = kws.create_stream()
    
    # 配置 PyAudio
    sample_rate = args.sample_rate
    chunk_size = int(args.chunk_duration * sample_rate)  # 每次读取的采样点数
    
    p = pyaudio.PyAudio()
    
    try:
        # 打开麦克风输入流
        audio_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk_size,
        )
        
        logger.info("=" * 60)
        logger.info("关键词检测已启动！请对着麦克风说出关键词...")
        logger.info(f"关键词文件: {args.keywords_file}")
        logger.info("按 Ctrl+C 停止程序")
        logger.info("=" * 60)
        
        detection_count = 0
        
        while True:
            # 从麦克风读取音频数据
            audio_data = audio_stream.read(chunk_size, exception_on_overflow=False)
            
            # 将 bytes 转换为 numpy array
            samples_int16 = np.frombuffer(audio_data, dtype=np.int16)
            samples_float32 = samples_int16.astype(np.float32) / 32768.0
            
            # 将音频数据送入关键词检测器
            stream.accept_waveform(sample_rate, samples_float32)
            
            # 执行检测
            while kws.is_ready(stream):
                kws.decode_stream(stream)
                result = kws.get_result(stream)
                
                if result:
                    detection_count += 1
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    
                    # 打印检测日志
                    logger.info("=" * 40)
                    logger.info(f"🎯 检测到关键词！第 {detection_count} 次")
                    logger.info(f"   关键词: {result}")
                    logger.info(f"   时间: {timestamp}")
                    logger.info("=" * 40)
                    
                    # 重要：检测到关键词后必须重置 stream
                    kws.reset_stream(stream)
                    
    except KeyboardInterrupt:
        logger.info("\n程序已停止（用户中断）")
    finally:
        # 清理资源
        audio_stream.stop_stream()
        audio_stream.close()
        p.terminate()
        logger.info(f"总共检测到 {detection_count} 次关键词")


if __name__ == "__main__":
    main()