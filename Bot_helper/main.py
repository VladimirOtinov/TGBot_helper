import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from config import (
    TOKEN, SERVER, EMAIL_PASSWORD, SUPPORT_EMAIL, BOT_EMAIL, PORT
)


bot = Bot(token=TOKEN)
dp = Dispatcher()

#создает большую нагрузку в случае большого количества запросов к боту
logging.basicConfig(level=logging.INFO)

@dp.message(CommandStart(deep_link=False))
async def handler_start(message: Message):
    #функция для ответа пользователю если получено сообщение без depp link
    print("Переход без ссылки")
    await message.answer("Добрый день")


@dp.message(CommandStart(deep_link=True))
async def handle_start(message: Message):
    #функция для сохраннения аргумента из deep link; отправка приветствия
    deep_link_id = message.get_args()
    await message.answer(f"Для теста, параметр ссылки: {deep_link_id}")
    #await message.answer("Добрый день! Я бот для передачи информации в тех. поддержку. "
    #                     "Опишите вашу ошибку, я передам ее нашим специалистам.")
    #сохранение ссылки в контексте пользователя
    await bot.set_state(chat_id=message.chat.id, user_id=message.from_user.id,
                        state='deep_link_id', data={'id': deep_link_id})


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    #запуск бота
    import asyncio
    asyncio.run(main())
