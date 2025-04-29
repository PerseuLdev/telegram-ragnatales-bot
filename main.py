import logging
import threading
import re
import os
import time
import json
import asyncio
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
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Servidor web iniciado na porta {port}")
    server.serve_forever()

# Função que coleta o menor preço, local e preço médio usando requests e BeautifulSoup
async def get_item_info(item_name):
    # Headers para simular um navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://ragnatales.com.br/db/items',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        # Primeira requisição para buscar a lista de itens disponíveis
        search_url = f"https://ragnatales.com.br/api/db/items?filter={item_name}"
        search_response = requests.get(search_url, headers=headers)
        search_response.raise_for_status()
        
        # Tenta processar a resposta JSON
        search_data = search_response.json()
        
        # Verfica se encontrou algum item
        if not search_data or 'data' not in search_data or not search_data['data']:
            return f"❌ O item '{item_name}' não foi encontrado."
        
        # Pega o primeiro item da lista (mais relevante)
        first_item = search_data['data'][0]
        item_id = first_item['id']
        item_name = first_item['name']
        
        # Busca informações detalhadas do item
        item_url = f"https://ragnatales.com.br/api/db/items/{item_id}"
        item_response = requests.get(item_url, headers=headers)
        item_response.raise_for_status()
        item_data = item_response.json()
        
        # Extrai preço médio, se disponível
        media_price = None
        if 'prices' in item_data and 'averagePrice' in item_data['prices']:
            media_price = format(item_data['prices']['averagePrice'], ',').replace(',', '.')
        
        # Busca detalhes das lojas que vendem o item
        shops_url = f"https://ragnatales.com.br/api/db/items/{item_id}/shops"
        shops_response = requests.get(shops_url, headers=headers)
        shops_response.raise_for_status()
        shops_data = shops_response.json()
        
        lowest_price = float('inf')
        lowest_location = ""
        
        # Processa cada loja para encontrar o menor preço
        if shops_data and 'data' in shops_data and shops_data['data']:
            for shop in shops_data['data']:
                if 'price' not in shop:
                    continue
                    
                price = float(shop['price'])
                
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

def main():
    # Inicia o servidor web em uma thread separada
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Inicia o bot do Telegram
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot está rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
