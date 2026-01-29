import os
import requests


def enviar_telegram(msg, token=None, chat_id=None):
    """
    Envia mensagem para o Telegram. token/chat_id podem ser passados ou
    obtidos de variáveis de ambiente TELEGRAM_TOKEN / TELEGRAM_CHAT_ID.
    """
    TELEGRAM_TOKEN = token or os.environ.get('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = chat_id or os.environ.get('TELEGRAM_CHAT_ID')

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f" [!] Sem config de Telegram. Msg seria: {msg}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro Telegram: {e}")
