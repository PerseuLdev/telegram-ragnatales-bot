PromoTales
Um bot de Telegram que pesquisa o item mais barato no market do site Ragnatales.

🚀 Funcionalidades:
Pesquisa automática do preço mais barato de um item.

Informa a localização (@market) onde o item foi encontrado.

Calcula e informa o preço médio das lojas.

Bot hospedado na nuvem (Render.com).

🛠 Tecnologias utilizadas:
Python 3.11

Selenium

python-telegram-bot 20.7

ChromeDriver (no ambiente local)

📄 Requisitos para rodar localmente:
Python 3.11 ou superior

Instalar as dependências:

bash
Copiar
Editar
pip install -r requirements.txt
Criar o arquivo .env (se preferir organizar melhor) ou configurar a variável BOT_TOKEN no seu código.

📦 Deploy na Render
Arquivos importantes para o deploy:

Procfile

bash
Copiar
Editar
worker: python promotales-bot.py
requirements.txt

Copiar
Editar
python-telegram-bot==20.7
selenium
Passos para subir na Render:

Faça o push do projeto para o GitHub.

No painel da Render, crie um novo serviço do tipo "Background Worker".

Conecte o repositório do GitHub.

Confirme que o build está instalando as dependências corretas.

Pronto! Seu bot ficará online 24/7 🚀

✉️ Como usar:
Abra o Telegram.

Procure pelo @PromoTales

Envie o nome de um item para pesquisar.

O bot responderá com o preço mais barato e a média de preços!

📝 Observação:
Algumas funções do Selenium são usadas apenas para navegar e extrair informações do site.

O bot não faz compras nem interage no market, apenas consulta informações.

Feito com ❤️ por Perseu
