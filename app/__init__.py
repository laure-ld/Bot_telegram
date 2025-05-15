from telegram import Bot
from telegram.ext import Dispatcher
from app.config import TELEGRAM_TOKEN

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)
