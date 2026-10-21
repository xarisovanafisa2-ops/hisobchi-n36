@echo off
chcp 65001 > nul
title GitHub ga yuklash (Push)

echo ===================================================
echo     GitHub ga loyihani yuklash (Push)
echo ===================================================
echo.

"%LOCALAPPDATA%\Programs\Git\cmd\git.exe" push -u origin main

echo.
if %errorlevel% equ 0 (
    echo ===================================================
    echo     Muvaffaqiyatli GitHub ga yuklandi!
    echo ===================================================
) else (
    echo ===================================================
    echo     Xatolik yuz berdi. Iltimos GitHub token yoki
    echo     parolni tekshiring.
    echo ===================================================
)
echo.
pause
