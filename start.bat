@echo off
chcp 65001 >nul
title Drunken_Butterfly

echo ============================================
echo   🦋 Drunken_Butterfly - 数据研究 Agent
echo ============================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查虚拟环境是否存在
if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境 .venv
    echo 请先运行: python -m venv .venv
    pause
    exit /b 1
)

:: 检查 .env 文件
if not exist ".env" (
    echo [提示] 未找到 .env 文件
    echo 正在从 .env.example 复制模板...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [提示] 已创建 .env 文件，请编辑填入 API Key 后重新启动
        start notepad ".env"
    ) else (
        echo [错误] 未找到 .env.example 模板文件
    )
    pause
    exit /b 1
)

:: 清除 Python 和 Streamlit 缓存（防止旧代码残留）
echo [信息] 正在清除缓存...
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist ".streamlit\cache" rmdir /s /q ".streamlit\cache"
del /f /s /q "cached_data.pkl" 2>nul

:: 启动 Streamlit
echo [信息] 正在启动 Streamlit...
echo [信息] 浏览器自动打开后即可使用
echo.
call .venv\Scripts\activate.bat && streamlit run app.py

:: 如果出错则暂停
if %errorlevel% neq 0 (
    echo.
    echo [错误] Streamlit 启动失败，请检查配置
    pause
)