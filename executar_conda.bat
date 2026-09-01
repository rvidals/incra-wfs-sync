@echo off
setlocal enabledelayedexpansion

echo ========================================
echo ATUALIZADOR WFS
echo Data: %date% %time%
echo ========================================

REM Definir caminhos
set CONDA_PATH=C:\Users\rogerio.siqueira\AppData\Local\miniconda3
set ENV_NAME=geopy_311
set SCRIPT_DIR=%~dp0

REM Ir para o diretório do script
cd /d "%SCRIPT_DIR%"

echo Diretorio: %CD%
echo Ambiente Conda: %ENV_NAME%

REM Ativar o ambiente Conda
call "%CONDA_PATH%\Scripts\activate.bat" "%CONDA_PATH%"
if errorlevel 1 (
    echo ERRO: Falha ao ativar o Conda
    echo %date% %time% - ERRO_ATIVACAO >> logs\erro.log
    exit /b 1
)

call conda activate %ENV_NAME%
if errorlevel 1 (
    echo ERRO: Falha ao ativar o ambiente %ENV_NAME%
    echo %date% %time% - ERRO_AMBIENTE >> logs\erro.log
    exit /b 1
)

echo Ambiente ativado: %ENV_NAME%
echo Python: 
python --version

REM Executar o script Python
echo.
echo Executando atualizador...
python atualizador_wfs.py

REM Capturar código de saída
set SCRIPT_ERROR=%errorlevel%

REM Desativar ambiente
call conda deactivate

REM Verificar resultado
if %SCRIPT_ERROR% neq 0 (
    echo.
    echo ERRO: Script falhou com codigo %SCRIPT_ERROR%
    echo %date% %time% - ERRO_CODIGO_%SCRIPT_ERROR% >> logs\erro.log
    exit /b %SCRIPT_ERROR%
) else (
    echo.
    echo SUCESSO: Atualizacao concluida
    echo %date% %time% - SUCESSO >> logs\sucesso.log
)

echo ========================================
exit /b 0