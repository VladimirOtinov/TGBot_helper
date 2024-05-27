import json
import logging
import asyncio
import aiosmtplib
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN, SMTP_SERVER, SMTP_PORT, SUPPORT_EMAIL, BOT_EMAIL, EMAIL_PASSWORD

# Настройка бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Определение класса состояния
class Form(StatesGroup):
    waiting_for_message = State()
    waiting_for_send = State()


# Обработчик команды /start
@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    args = message.text.split()
    await state.update_data(user_id=message.from_user.id)
    if len(args) > 1:
        deep_link_id = args[1]
        await state.update_data(deep_link_id=deep_link_id)
        await message.answer(
            "Добрый день! Я бот для передачи информации в тех. поддержку. "
            "Опишите вашу ошибку в _одном сообщении_, я передам ее нашим специалистам.",
            parse_mode="Markdown"
        )
        await state.set_state(Form.waiting_for_message)
    else:
        await message.answer("Добрый день")


# Обработчик обычных сообщений
@dp.message(Form.waiting_for_message)
async def handle_message(message: Message, state: FSMContext):
    await state.update_data(user_message=message.text)
    await message.answer("Ваше сообщение было сохранено. Для отправки нажмите или введите /send.")
    await state.set_state(Form.waiting_for_send)


# Обработчик команды /send
@dp.message(Command(commands=["send"]))
async def handle_send(message: Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    deep_link_id = state_data.get("deep_link_id")
    user_message = state_data.get("user_message")

    if user_message:
        # Формирование данных для отправки по почте
        email_data = {
            'user_id': user_id,
            'message': user_message
        }
        email_content = json.dumps(email_data, indent=4, ensure_ascii=False)
        subject = f"param: {deep_link_id} uid: {user_id}"
        await send_email(email_content, subject)
        await message.answer("Ваше обращение было передано в тех. поддержку")
        await state.clear()
    else:
        await message.answer("Что-то пошло не так. Пожалуйста, опишите вашу ошибку еще раз.")


async def send_email(content: str, subject: str):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart()
    msg['From'] = BOT_EMAIL
    msg['To'] = SUPPORT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'plain'))

    await aiosmtplib.send(
        msg,
        hostname=SMTP_SERVER,
        port=SMTP_PORT,
        username=BOT_EMAIL,
        password=EMAIL_PASSWORD,
        use_tls=True
    )


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
