#!/bin/bash
# 树莓派快速部署脚本

echo "=========================================="
echo "树莓派快速部署脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
   echo "请不要使用 root 用户运行此脚本"
   exit 1
fi

# 安装系统依赖
echo ""
echo "1. 检查并安装 mpg123..."
if ! command -v mpg123 &> /dev/null; then
    echo "   正在安装 mpg123..."
    sudo apt update
    sudo apt install -y mpg123
else
    echo "   ✓ mpg123 已安装"
fi

# 检查 Python
echo ""
echo "2. 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "   错误: 未找到 python3，请先安装 Python 3"
    exit 1
else
    PYTHON_VERSION=$(python3 --version)
    echo "   ✓ $PYTHON_VERSION"
fi

# 检查 pip
echo ""
echo "3. 检查 pip..."
if ! command -v pip3 &> /dev/null; then
    echo "   正在安装 pip..."
    sudo apt install -y python3-pip
else
    echo "   ✓ pip3 已安装"
fi

# 安装 Python 依赖
echo ""
echo "4. 安装 Python 依赖..."
pip3 install -r requirements.txt --user

# 检查音乐文件
echo ""
echo "5. 检查音乐文件..."
MUSIC_DIR="$(dirname "$0")/music"
if [ -d "$MUSIC_DIR" ]; then
    if [ -f "$MUSIC_DIR/alarm.mp3" ] && [ -f "$MUSIC_DIR/white.mp3" ]; then
        echo "   ✓ 音乐文件存在"
    else
        echo "   ⚠ 警告: 音乐文件不完整"
        echo "      需要的文件: alarm.mp3, white.mp3"
    fi
else
    echo "   ⚠ 警告: music 文件夹不存在"
fi

echo ""
echo "=========================================="
echo "部署准备完成！"
echo "=========================================="
echo ""
echo "启动服务器："
echo "  cd $(dirname "$0")"
echo "  uvicorn server:app --host 0.0.0.0 --port 8000"
echo ""
echo "或直接运行："
echo "  python3 server.py"
echo ""

