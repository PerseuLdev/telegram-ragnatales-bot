import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
import os
from dotenv import load_dotenv

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

# Função que coleta o menor preço, local e preço médio
def get_item_info(item_name):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Caminhos do Chrome e Chromedriver
    chrome_binary = os.environ.get("GOOGLE_CHROME_SHIM", "/usr/bin/google-chrome")
    chrome_driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    chrome_options.binary_location = chrome_binary
    service = Service(executable_path=chrome_driver_path)

    try:
        navegador = webdriver.Chrome(service=service, options=chrome_options)
        navegador.get("https://ragnatales.com.br/db/items")
        time.sleep(5)

        try:
            campo_pesquisar = navegador.find_element(By.CSS_SELECTOR, "input[placeholder='Filtrar por nome']")
            campo_pesquisar.click()
            campo_pesquisar.send_keys(item_name, Keys.ENTER)
            time.sleep(3)

            item = navegador.find_element(By.XPATH, '//a[starts-with(@href, "/db/items/")]')
            item.click()
            time.sleep(3)

            try:
                media_texto = navegador.find_element(By.XPATH, '//div[contains(text(), "A Média de preço deste item é de")]').text
                media_price_match = re.search(r"[\d.,]+", media_texto)
                media_price = media_price_match.group(0) if media_price_match else None
            except:
                media_price = None

            botao_lojas = navegador.find_element(By.XPATH, '//button[contains(., "lojas")]')
            navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_lojas)
            time.sleep(1)
            ActionChains(navegador).move_to_element(botao_lojas).pause(0.5).click().perform()
            time.sleep(3)

            lojas = navegador.find_elements(By.CSS_SELECTOR, ".rounded-sm.bg-white.text-black.px-4.py-2.text-base")
            lowest_price = float('inf')
            lowest_location = ""

            for loja in lojas:
                text = loja.text
                price_match = re.search(r"\b([\d\.]+,\d{2}|\d{1,3}(?:\.\d{3})+)\b", text)
                if not price_match:
                    continue
                price_str = price_match.group(1)
                price = float(price_str.replace(".", "").replace(",", "."))

                location_match = re.search(r"@market (\d+)/(\d+)", text)
                location = f"@market {location_match.group(1)}/{location_match.group(2)}" if location_match else ""

                if price < lowest_price:
                    lowest_price = price
                    lowest_location = location

            navegador.quit()

            if lowest_price != float('inf'):
                formatted_price = f"{int(lowest_price):,}".replace(",", ".")
                resposta = f"🛒 O {item_name} mais barato(a) encontrado(a) custa: {formatted_price} zenys e está no {lowest_location}."
                if media_price:
                    resposta += f"\n📊 Média de preço deste item: {media_price} zenys."
            else:
                resposta = f"❌ O item '{item_name}' não consta no market."

            return resposta

        except Exception as e:
            logging.error(f"Erro ao buscar item: {str(e)}")
            navegador.quit()
            return f"❌ O item '{item_name}' não foi encontrado. Erro: {str(e)}"

    except Exception as e:
        logging.error(f"Erro ao iniciar navegador: {str(e)}")
        return f"❌ Erro ao iniciar o navegador: {str(e)}"

# Função que trata mensagens de texto
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.reply_text("🔎 Buscando informações...")
    resposta = get_item_info(user_input)
    await update.message.reply_text(resposta)

# Mensagem de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envie o nome de um item para buscar o mais barato no market do Ragnatales!")

def main():
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot está rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
