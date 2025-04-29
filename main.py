import logging
import threading
import re
import os
import time
import json
import asyncio
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Carrega as variáveis do .env
load_dotenv()

# Acessa o token
TOKEN = os.getenv("BOT_TOKEN")

# Ativa logs para depuração
logging.basicConfig(level=logging.INFO)

# Servidor web simples para manter o Render ativo
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Ragnatales Bot is running!')

def run_server():
    global http_server
    port = int(os.environ.get("PORT", 10000))
    http_server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Servidor web iniciado na porta {port}")
    try:
        http_server.serve_forever()
    except Exception as e:
        logging.error(f"Erro no servidor HTTP: {str(e)}")
    finally:
        if http_server:
            http_server.server_close()
            print("Servidor HTTP fechado")

# Função que coleta o menor preço, local e preço médio usando requests e BeautifulSoup
async def get_item_info(item_name):
    # Headers para simular um navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://ragnatales.com.br/db/items',
        'Origin': 'https://ragnatales.com.br',
        'Connection': 'keep-alive'
    }
    
    try:
        # Primeira requisição para buscar a lista de itens disponíveis
        logging.info(f"Buscando item: {item_name}")
        
        # Utiliza o endpoint de API correto com parâmetros adequados
        search_url = f"https://ragnatales.com.br/api/db/items"
        params = {
            'filter': item_name,
            'page': 1,
            'itemsPerPage': 10
        }
        
        search_response = requests.get(search_url, headers=headers, params=params)
        search_response.raise_for_status()
        
        # Tenta processar a resposta JSON
        search_data = search_response.json()
        logging.info(f"Resposta da busca: {len(search_data.get('data', [])) if 'data' in search_data else 'Sem dados'}")
        
        # Verifica se encontrou algum item
        if not search_data or 'data' not in search_data or not search_data['data']:
            return f"❌ O item '{item_name}' não foi encontrado."
        
        # Pega o primeiro item da lista (mais relevante)
        first_item = search_data['data'][0]
        item_id = first_item['id']
        item_name = first_item['name']
        
        logging.info(f"Item encontrado: {item_name} (ID: {item_id})")
        
        # Busca informações detalhadas do item
        item_url = f"https://ragnatales.com.br/api/db/items/{item_id}"
        item_response = requests.get(item_url, headers=headers)
        item_response.raise_for_status()
        item_data = item_response.json()
        
        # Extrai preço médio, se disponível
        media_price = None
        if item_data and 'prices' in item_data and item_data['prices'] and 'averagePrice' in item_data['prices']:
            media_price = format(item_data['prices']['averagePrice'], ',').replace(',', '.')
            logging.info(f"Preço médio: {media_price}")
        
        # Busca detalhes das lojas que vendem o item
        shops_url = f"https://ragnatales.com.br/api/db/items/{item_id}/shops"
        shops_response = requests.get(shops_url, headers=headers)
        shops_response.raise_for_status()
        shops_data = shops_response.json()
        
        logging.info(f"Lojas encontradas: {len(shops_data.get('data', [])) if 'data' in shops_data else 'Sem lojas'}")
        
        lowest_price = float('inf')
        lowest_location = ""
        
        # Processa cada loja para encontrar o menor preço
        if shops_data and 'data' in shops_data and shops_data['data']:
            for shop in shops_data['data']:
                if 'price' not in shop:
                    continue
                    
                price = float(shop['price'])
                logging.info(f"Loja com preço: {price}")
                
                # Extrai a localização da loja
                location = ""
                if 'coords' in shop and 'x' in shop['coords'] and 'y' in shop['coords']:
                    location = f"@market {shop['coords']['x']}/{shop['coords']['y']}"
                
                if price < lowest_price:
                    lowest_price = price
                    lowest_location = location
        
        # Formata a resposta
        if lowest_price != float('inf'):
            formatted_price = f"{int(lowest_price):,}".replace(",", ".")
            resposta = f"🛒 O {item_name} mais barato(a) encontrado(a) custa: {formatted_price} zenys e está no {lowest_location}."
            if media_price:
                resposta += f"\n📊 Média de preço deste item: {media_price} zenys."
        else:
            resposta = f"❌ O item '{item_name}' não consta no market."
            
        return resposta
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição HTTP: {str(e)}")
        return f"❌ Erro ao buscar informações do item '{item_name}'. Verifique o nome e tente novamente."
    
    except ValueError as e:
        logging.error(f"Erro ao processar dados JSON: {str(e)}")
        return f"❌ Não foi possível processar as informações do item '{item_name}'."
    
    except Exception as e:
        logging.error(f"Erro inesperado: {str(e)}")
        return f"❌ Ocorreu um erro inesperado ao buscar '{item_name}'. Por favor, tente novamente mais tarde."

# Função que trata mensagens de texto
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.reply_text("🔎 Buscando informações...")
    resposta = await get_item_info(user_input)
    await update.message.reply_text(resposta)

# Mensagem de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envie o nome de um item para buscar o mais barato no market do Ragnatales!")

# Variável global para controlar o servidor HTTP
http_server = None

# Função para lidar com a finalização do programa
def shutdown_handler(sig, frame):
    print("🛑 Encerrando o bot...")
    
    # Encerra o servidor HTTP se estiver em execução
    global http_server
    if http_server:
        http_server.shutdown()
        print("✓ Servidor HTTP encerrado")
    
    # Encerra o processo Python
    print("🔄 Bot finalizado corretamente")
    sys.exit(0)

def main():
    # Registra manipuladores de sinal para encerramento limpo
    signal.signal(signal.SIGINT, shutdown_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_handler)  # kill command
    
    # Verifica se não há outra instância em execução
    try:
        # Tenta criar um arquivo de trava
        with open('bot.lock', 'w') as lock_file:
            lock_file.write(str(os.getpid()))
    except Exception as e:
        logging.error(f"Erro ao criar arquivo de trava: {str(e)}")
        # Continua mesmo se não conseguir criar o arquivo
    
    # Inicia o servidor web em uma thread separada
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Inicia o bot do Telegram
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot está rodando...")
    
    try:
        app.run_polling()
    finally:
        # Limpa recursos ao encerrar
        if os.path.exists('bot.lock'):
            try:
                os.remove('bot.lock')
            except:
                pass
        print("🔄 Bot finalizado")

if __name__ == "__main__":
    main()
