import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import chromedriver_autoinstaller
import time
import re
import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

# Acessa o token
TOKEN = os.getenv("BOT_TOKEN")

# Configura o log para verificar problemas
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configura o driver do Chrome para ambiente de container
def get_chrome_driver():
    chrome_options = Options()
    
    # Verifica se está rodando em container
    is_container = os.getenv("IS_CONTAINER", "False").lower() == "true"
    
    if is_container:
        # Configurações para ambiente de container
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.binary_location = "/usr/bin/google-chrome"
        driver = webdriver.Chrome(options=chrome_options)
    else:
        # Para ambiente local
        chromedriver_autoinstaller.install()
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver

# Função que coleta o menor preço, local e preço médio
def get_item_info(item_name):
    navegador = get_chrome_driver()
    navegador.set_window_size(1920, 1080)  # Definir tamanho da janela mesmo em headless
    
    try:
        logger.info(f"Buscando informações para: {item_name}")
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
            except Exception as e:
                logger.warning(f"Não foi possível encontrar o preço médio: {e}")
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
            logger.error(f"Erro ao processar página do item: {e}")
            navegador.quit()
            return f"❌ Erro ao buscar '{item_name}'. Verifique se o nome está correto."
            
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        try:
            navegador.quit()
        except:
            pass
        return f"❌ Ocorreu um erro ao processar sua solicitação para '{item_name}'."

# Função para lidar com mensagens de texto
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.reply_text("🔎 Buscando informações...")
    
    try:
        resposta = get_item_info(user_input)
        await update.message.reply_text(resposta)
    except Exception as e:
        logger.error(f"Erro não tratado: {e}")
        await update.message.reply_text(f"❌ Ocorreu um erro inesperado. Tente novamente mais tarde.")

# Mensagem de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envie o nome de um item para buscar o mais barato no market do Ragnatales!")

# Função para verificar se o bot está ativo
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot está online e funcionando!")

def main():
    logger.info("Iniciando o bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Registra os handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot está rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
