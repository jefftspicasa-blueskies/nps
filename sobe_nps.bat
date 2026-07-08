@echo off
title Gerenciador de Serviços Streamlit

echo ========================================
echo VERIFICANDO SERVICOS EM EXECUCAO...
echo ========================================

:: Matar processos existentes nas portas 8501 e 8502
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8501" ^| find "LISTENING"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8502" ^| find "LISTENING"') do taskkill /f /pid %%a 2>nul

echo Portas liberadas. Iniciando servicos...

start "Cloudflare Tunnel" cmd /k cloudflared tunnel run 2f935f2e-9246-4056-9b96-2432c368cc37
timeout /t 3 /nobreak >nul

start "Streamlit App (8501)" cmd /k python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
timeout /t 2 /nobreak >nul

start "Streamlit Admin (8502)" cmd /k python -m streamlit run admin_dashboard.py --server.address 0.0.0.0 --server.port 8502

echo ========================================
echo TODOS OS SERVICOS INICIADOS!
echo ========================================
echo Cloudflare Tunnel: Ativo
echo Streamlit App: http://localhost:8501
echo Streamlit Admin: http://localhost:8502
echo ========================================
echo Pressione qualquer tecla para fechar...
pause >nul