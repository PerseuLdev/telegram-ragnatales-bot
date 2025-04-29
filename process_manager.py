#!/usr/bin/env python3
"""
Script para gerenciar e verificar instâncias do bot do Ragnatales.
Este script verifica se já existe uma instância em execução e termina processos antigos se necessário.
"""

import os
import sys
import signal
import logging
import subprocess
import time

# Configura o logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("ProcessManager")

def get_bot_processes():
    """Retorna uma lista dos processos Python executando o bot"""
    try:
        result = subprocess.run(
            ["ps", "-ef"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        processes = []
        for line in result.stdout.split("\n"):
            if "python" in line and "main.py" in line and "grep" not in line:
                processes.append(line)
        
        return processes
    except Exception as e:
        logger.error(f"Erro ao buscar processos: {e}")
        return []

def kill_process(pid):
    """Mata um processo pelo PID"""
    try:
        logger.info(f"Tentando matar processo {pid}")
        os.kill(int(pid), signal.SIGTERM)
        time.sleep(1)
        
        # Verifica se o processo ainda existe
        try:
            os.kill(int(pid), 0)  # Sinal 0 apenas verifica se o processo existe
            logger.warning(f"Processo {pid} ainda em execução, enviando SIGKILL")
            os.kill(int(pid), signal.SIGKILL)
        except OSError:
            logger.info(f"Processo {pid} finalizado com sucesso")
            return True
            
        return True
    except Exception as e:
        logger.error(f"Erro ao matar processo {pid}: {e}")
        return False

def cleanup_old_processes():
    """Identifica e mata processos antigos do bot"""
    processes = get_bot_processes()
    
    # Ignora o processo atual
    current_pid = os.getpid()
    
    for process in processes:
        parts = process.split()
        if len(parts) < 2:
            continue
            
        pid = parts[1]
        
        # Verifica se não é o processo atual
        if int(pid) != current_pid and int(pid) != os.getppid():
            logger.info(f"Encontrado processo antigo: {process}")
            kill_process(pid)

def check_lock_file():
    """Verifica se existe um arquivo de trava e se o processo nele ainda está em execução"""
    if os.path.exists('bot.lock'):
        try:
            with open('bot.lock', 'r') as lock_file:
                pid = lock_file.read().strip()
                
                if pid:
                    # Verifica se o processo ainda está em execução
                    try:
                        os.kill(int(pid), 0)
                        logger.warning(f"Bot já está em execução (PID: {pid})")
                        return int(pid)
                    except OSError:
                        # Processo não existe mais
                        logger.info("Arquivo de trava encontrado, mas o processo não está em execução")
                        os.remove('bot.lock')
        except Exception as e:
            logger.error(f"Erro ao verificar arquivo de trava: {e}")
            try:
                os.remove('bot.lock')
            except:
                pass
    
    return None

if __name__ == "__main__":
    logger.info("Verificando processos antigos do bot...")
    
    # Verifica o arquivo de trava
    existing_pid = check_lock_file()
    if existing_pid:
        kill_process(existing_pid)
    
    # Limpa outros processos antigos
    cleanup_old_processes()
    
    logger.info("Limpeza de processos concluída. Pronto para iniciar o bot.")
