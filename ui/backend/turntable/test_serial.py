#!/usr/bin/env python3
"""转盘串口测试工具

独立测试程序，用于验证串口通信功能。
可以手动输入扇区编号（1-6）测试发送到 STM32。

使用方法：
    python test_serial.py
"""
import sys
import os
import logging

# 添加上级目录到 Python 路径，以便导入 turntable_serial 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turntable_serial import TurntableSerial, SERIAL_PORT, BAUD_RATE, DATA_FORMAT

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def print_config():
    """打印当前串口配置"""
    print("\n" + "="*50)
    print("转盘串口测试工具")
    print("="*50)
    print(f"串口设备: {SERIAL_PORT}")
    print(f"波特率: {BAUD_RATE}")
    print(f"数据格式: {DATA_FORMAT}")
    print("="*50 + "\n")


def main():
    """主测试程序"""
    print_config()

    # 初始化串口连接
    try:
        turntable = TurntableSerial()
        print("✓ 串口连接成功！\n")
    except Exception as e:
        print(f"✗ 串口连接失败: {e}")
        print("\n提示：")
        print(f"  1. 检查串口设备是否存在: ls /dev/tty*")
        print(f"  2. 检查串口权限: sudo chmod 666 {SERIAL_PORT}")
        print(f"  3. 或添加用户到 dialout 组: sudo usermod -a -G dialout $USER")
        return 1

    # 交互式测试循环
    print("请输入扇区编号（1-6），输入 'q' 或 'quit' 退出：\n")

    try:
        while True:
            try:
                user_input = input("扇区编号 > ").strip()

                # 退出命令
                if user_input.lower() in ['q', 'quit', 'exit']:
                    print("\n退出测试工具...")
                    break

                # 空输入
                if not user_input:
                    continue

                # 转换为整数
                try:
                    sector = int(user_input)
                except ValueError:
                    print(f"✗ 输入错误：'{user_input}' 不是有效的数字，请输入 1-6\n")
                    continue

                # 验证范围
                if not (1 <= sector <= 6):
                    print(f"✗ 输入错误：{sector} 超出范围，请输入 1-6\n")
                    continue

                # 发送扇区命令
                print(f"→ 正在发送扇区 {sector}...")
                success = turntable.send_sector(sector)

                if success:
                    print(f"✓ 扇区 {sector} 发送成功！\n")
                else:
                    print(f"✗ 扇区 {sector} 发送失败\n")

            except KeyboardInterrupt:
                print("\n\n检测到 Ctrl+C，退出测试工具...")
                break

    finally:
        # 清理资源
        turntable.close()
        print("串口已关闭")

    return 0


if __name__ == "__main__":
    sys.exit(main())
