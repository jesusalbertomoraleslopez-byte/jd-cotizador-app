@echo off
title J&D Automation Industries - Cotizador & TPU
color 0A
echo =================================================================
echo        J&D AUTOMATION INDUSTRIES - SISTEMA DE COTIZACIONES
echo =================================================================
echo.
echo Iniciando servidor de produccion local...
echo.

cd /d "%~dp0"

echo Direcciones de Acceso en tu Red:
echo  - Local:   http://localhost:8502
echo  - Red LAN: http://192.168.11.95:8502
echo.
echo Presiona Ctrl+C para detener el servidor.
echo =================================================================
echo.

py -3 -m streamlit run app.py --server.port 8502 --server.headless true

pause
