#!/bin/bash
# Script para iniciar o bot com verificação de processos anteriores

echo "🔄 Verificando processos antigos do bot..."
python process_manager.py

echo "🚀 Iniciando bot..."
python main.py
