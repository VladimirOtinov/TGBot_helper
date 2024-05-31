import json
import logging
import asyncio
import aiosmtplib
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN, SMTP_SERVER, SMTP_PORT, SUPPORT_EMAIL, BOT_EMAIL, EMAIL_PASSWORD
from MessageStruct import MessageStruct

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
    await state.update_data(user_id=message.from_user.id, messages=[])
    if len(args) > 1:
        deep_link_id = args[1]
        await state.update_data(deep_link_id=deep_link_id)
        await message.answer(
            "Добрый день! Я бот для передачи информации в тех. поддержку. "
            "Опишите вашу проблему в нескольких сообщениях, затем отправьте /send для отправки сообщений.",
            parse_mode="Markdown"
        )
        await state.set_state(Form.waiting_for_message)
    else:
        await message.answer("Добрый день")
        await state.set_state(Form.waiting_for_message)

# Обработчик обычных сообщений
@dp.message(Form.waiting_for_message)
async def handle_message(message: Message, state: FSMContext):
    state_data = await state.get_data()
    messages = state_data.get("messages", [])

    # Формирование объекта MessageStruct
    message_struct = MessageStruct(
        text_message=message.text,
        uid=message.from_user.id,
        time_send=datetime.now().strftime("%H:%M:%S"),
        deep_link=state_data.get("deep_link_id", "")
    )

    messages.append(message_struct.to_json())
    await state.update_data(messages=messages)

    await message.answer("Ваше сообщение было сохранено. Для отправки всех сообщений введите /send.")

# Обработчик команды /send
@dp.message(Form.waiting_for_message, Command(commands=["send"]))
async def handle_send(message: Message, state: FSMContext):
    state_data = await state.get_data()
    messages = state_data.get("messages", [])

    if messages:
        # Формирование JSON-данных для отправки
        email_content = json.dumps(messages, indent=4, ensure_ascii=False)
        subject = f"param: {state_data.get('deep_link_id', '')} uid: {state_data.get('user_id', '')}"
        await send_email(email_content, subject)
        await message.answer("Ваше обращение было передано в тех. поддержку.")
        await state.clear()
    else:
        await message.answer("Нет сохраненных сообщений. Пожалуйста, опишите вашу проблему еще раз.")

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
