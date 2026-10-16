@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  电商价格对比工具 - Windows 打包脚本
echo ============================================
echo [1/3] 安装 PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :err

echo [2/3] 打包为单文件可执行程序...
python -m PyInstaller --noconfirm --onefile --name ecom-price-tool ^
  --add-data "web/static;web/static" ^
  desktop.py
if errorlevel 1 goto :err

echo [3/3] 打包完成！
echo 可执行文件位置：dist\ecom-price-tool.exe
echo 双击 dist\ecom-price-tool.exe 即可运行（会自动打开浏览器）。
pause
exit /b 0

:err
echo 打包失败：请确认已安装 Python 3 且可访问网络。
pause
exit /b 1
