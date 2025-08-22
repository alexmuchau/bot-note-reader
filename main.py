from Notion import Notion

import telebot
from qreader import QReader
from markitdown import MarkItDown
import cv2
import requests
from bs4 import BeautifulSoup
import re
import os

from dotenv import load_dotenv
load_dotenv()

class TelegramBot:
    def __init__(self, bot_token, notion_api_key, notion_database_id):
        self.bot = telebot.TeleBot(bot_token)
        self.notion = Notion(notion_api_key, notion_database_id)

    def main(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.bot.reply_to(message, "Hello! I'm your bot. How can I assist you today?")
            
        @self.bot.message_handler(commands=["note_url"])
        def handle_note_url(message: telebot.types.Message):
            command_len = len("note_url")
            note_url = message.text[command_len+1:].strip()
            
            items, market_name, buy_date, buy_total = self.get_note_infos(message, note_url)
            
            response_message = f"Market: {market_name}\nDate: {buy_date}\nTotal: {buy_total:.2f}\n\nItems:\n"
            for code, info in items.items():
                response_message += f"- {info['name']} (Code: {code}): {info['qtd']} x {info['vl_unit']:.2f} = {info['total']:.2f}\n"
            
            self.bot.reply_to(message, response_message)
        
        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message: telebot.types.Message):
            print("Photo received")
            photo = max(message.photo, key=lambda p: p.file_size)
            
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={photo.file_id}").json()
            file_path = res["result"]["file_path"]

            res = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}")
            with open("qr_code.png", "wb") as file:
                file.write(res.content)
            
            print("Photo saved as qr_code.png")
                
            qr_code_text = self.get_note_qr_code(message, "qr_code.png")
            market_name, buy_date, buy_total, items = self.get_note_infos(message, qr_code_text)
            
            response_message = self.insert_notion(market_name, buy_date, buy_total, items)
            
            self.bot.reply_to(message, response_message)
            
        self.bot.infinity_polling()
            

    def insert_notion(self, market_name, buy_date, buy_total, items):
        message = "==========================================\n"
        state, notion_message = self.notion.create_note_page(market_name, buy_date, buy_total, items)
        message += notion_message
        message += "\n=========================================="
        
        message += f"\nCompra no Mercado: {market_name}, em: {buy_date}, total: {buy_total:.2f}"
        message += "\n=========================================="
        message += "\nLista dos itens:"
        for code, info in items.items():
            message += f"\n- {info['name']} (Code: {code}): {info['qtd']} x {info['vl_unit']:.2f} = {info['total']:.2f}"
            
        return message
        
    
    def get_note_qr_code(self, message, path):
        decoded = self.qr_code_reader(path)
        qr_code_text = decoded[0] if decoded else "No QR code found."
        
        if qr_code_text is None:
            return self.bot.reply_to(message, "Não foi possível ler o QR Code da imagem enviada.")
        
        if qr_code_text is not None and "fazenda.pr.gov" not in qr_code_text:
            return self.bot.reply_to(message, "Essa foto não contém um QR Code de uma nota fiscal eletrônica do Paraná.")
        
        return qr_code_text

    def qr_code_reader(self, path):
        image = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)

        qreader = QReader()
        decoded_text = qreader.detect_and_decode(image=image)
        return decoded_text

    def get_note_infos(self, message, url: str):
        note_soup = self.get_html_content(url)
            
        if note_soup is None:
            return self.bot.reply_to(message, "Não foi possível acessar a URL do QR Code.")
        
        return self.get_html_note_infos(note_soup)
        
    def get_html_content(self, url: str):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return None
        
        return BeautifulSoup(response.text, "html.parser")

    def get_html_note_infos(self, soup: BeautifulSoup):
        items: dict[str, dict] = {}
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                code = tr.find_all("span", "RCod")[0].text.strip()
                code = code[code.find(":") + 2:-1]

                name = tr.find_all("span", "txtTit2")[0].text.strip()

                qtd = tr.find_all("span", "Rqtd")[0].text.strip()
                qtd = float(qtd[qtd.find(":") + 1:].replace(',', '.'))

                vl_unit = tr.find_all("span", "RvlUnit")[0].text.strip()
                vl_unit = float(vl_unit[vl_unit.find(":") + 2:].replace(',', '.'))

                total = float(tr.find_all("span", "valor")[0].text.strip().replace(',', '.'))

                if code in items:
                    items[code]["qtd"] += qtd
                    items[code]["total"] += total
                    continue

                items[code] = {
                    "name": name,
                    "qtd": qtd,
                    "vl_unit": vl_unit,
                    "total": total
                }
        
        market_name: str = soup.find_all("div", "txtTopo")[0].text.strip()

        date_pattern = r"\b\d{2}/\d{2}/\d{4}\b"
        buy_date = '-'.join(re.findall(date_pattern, soup.text)[0].split("/")[::-1])
        buy_total: float = float(soup.find_all("span", "totalNumb txtMax")[0].text.strip().replace(',', '.'))

        return market_name, buy_date, buy_total, items

    def markitdown(self, url):
        md = MarkItDown()
        result = md.convert(url)
        print(result.text_content)

if __name__ == "__main__":
    TOKEN = os.getenv("NOTE_READER_TOKEN")
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    TelegramBot(TOKEN, NOTION_API_KEY, NOTION_DATABASE_ID).main()