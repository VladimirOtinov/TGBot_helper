import json
import logging
import asyncio
import aiosmtplib
from datetime import datetime
from email import policy
from email.parser import BytesParser
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from imaplib import IMAP4_SSL
from config import TOKEN, SMTP_SERVER, SMTP_PORT, SUPPORT_EMAIL, BOT_EMAIL, EMAIL_PASSWORD, IMAP_SERVER, IMAP_PORT
from MessageStruct import MessageStruct

# Настройка бота и диспетчера
bot = Bot(token=TOKEN, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение класса состояния для FSM
class Form(StatesGroup):
    waiting_for_message = State()  # Состояние ожидания сообщения
    waiting_for_send = State()     # Состояние ожидания отправки сообщения

# Обработчик команды /start
@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    args = message.text.split()  # Разбиение текста сообщения на аргументы
    await state.update_data(user_id=message.from_user.id, chat_id=message.chat.id, messages=[])
    if len(args) > 1:  # Если есть дополнительные аргументы
        deep_link_id = args[1]  # Получение идентификатора deep link
        await state.update_data(deep_link_id=deep_link_id)
        await message.answer(
            "Добрый день! Я бот для передачи информации в тех. поддержку. "
            "Опишите вашу проблему в нескольких сообщениях, затем отправьте "
            "/send для отправки сообщений."
        )
        await state.set_state(Form.waiting_for_message)
    else:  # Если нет дополнительных аргументов
        await message.answer("Добрый день, перейдите, пожалуйста, по ссылке еще раз, "
                             "либо воспользуйтесь другой")
        await state.set_state(Form.waiting_for_message)

# Обработчик команды /send
@dp.message(Form.waiting_for_message, Command(commands=["send"]))
async def handle_send(message: Message, state: FSMContext):
    state_data = await state.get_data()  # Получение данных состояния
    messages = state_data.get("messages", [])  # Получение сохраненных сообщений из состояния

    if messages:  # Если есть сохраненные сообщения
        # Формирование JSON-данных для отправки
        email_content = json.dumps(messages, indent=4, ensure_ascii=False)
        subject = (f"param: {state_data.get('deep_link_id', '')} "
                   f"uid: {state_data.get('user_id', '')} "
                   f"chat_id: {state_data.get('chat_id', '')}")
        await send_email(email_content, subject)  # Отправка электронного письма
        await message.answer("Ваше обращение было передано в тех. поддержку.")
        await state.clear()  # Очистка состояния FSM
    else:  # Если нет сохраненных сообщений
        await message.answer("Нет сохраненных сообщений. "
                             "Пожалуйста, опишите вашу проблему еще раз.")

# Обработчик сообщений с описанием ошибки
@dp.message(Form.waiting_for_message)
async def handle_message(message: Message, state: FSMContext):
    state_data = await state.get_data()
    messages = state_data.get("messages", [])  # Получение сохраненных сообщений из состояния

    # Формирование объекта MessageStruct
    message_struct = MessageStruct(
        text_message=message.text,
        uid=message.from_user.id,
        time_send=datetime.now().strftime("%H:%M:%S"),
        deep_link=state_data.get("deep_link_id", ""),
        chat_id=message.chat.id
    )

    messages.append(message_struct.to_json())  # Добавление нового сообщения в список сохраненных
    await state.update_data(messages=messages)  # Обновление данных состояния

    await message.answer("Ваше сообщение было сохранено. "
                         "Для отправки всех сообщений введите /send.")

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


async def check_email():
    from bs4 import BeautifulSoup
    while True:
        logging.info("Проверка наличия новых писем...")  # Логирование проверки новых писем
        with IMAP4_SSL(IMAP_SERVER, IMAP_PORT) as mail:  # Подключение к IMAP серверу с использованием SSL
            mail.login(BOT_EMAIL, EMAIL_PASSWORD)  # Аутентификация на почтовом сервере
            mail.select('inbox')  # Выбор папки "входящие"

            status, messages = mail.search(None, '(UNSEEN)')  # Поиск непрочитанных писем
            logging.info(f"Статус проверки писем: {status}")  # Логирование статуса поиска новых писем
            logging.info(f"Найдено {len(messages[0].split())} новых писем.")  # Логирование количества новых писем

            for num in messages[0].split():  # Перебор идентификаторов новых писем
                status, data = mail.fetch(num, '(RFC822)')  # Получение данных письма по его идентификатору
                logging.info(f"Найдено письмо ID {num}, статус: {status}")  # Логирование статуса получения письма

                # Парсинг письма в объект BytesParser
                email_message = BytesParser(policy=policy.default).parsebytes(data[0][1])
                for part in email_message.walk():  # Перебор частей письма
                    if part.get_content_type() == 'text/html':  # Проверка типа части письма (HTML)
                        body = part.get_payload(decode=True).decode()  # Получение HTML содержимого письма
                        logging.info(f"Содержимое письма: {body}")  # Логирование HTML содержимого письма
                        try:
                            # Использование BeautifulSoup для извлечения текста из HTML
                            soup = BeautifulSoup(body, 'html.parser')
                            text = soup.get_text(separator='', strip=True)  # Извлечение текста из HTML, удаление лишних пробелов
                            message_data = json.loads(text)  # Парсинг JSON данных из текста
                            await process_support_message(message_data)  # Обработка полученных данных
                        except json.JSONDecodeError:
                            logging.error("Ошибка декодинга JSON из письма")  # Логирование ошибки при декодировании JSON

        await asyncio.sleep(60)  # Пауза в выполнении для проверки почты каждые 60 секунд


async def process_support_message(data):
    uid = data.get('uid')  # Извлечение идентификатора пользователя
    chat_id = data.get('chat_id')  # Извлечение идентификатора чата
    text_message = data.get('text_message')  # Извлечение текста сообщения

    logging.info(f"Обработка сообщения службы поддержки: {data}")  # Логирование обработки сообщения
    await bot.send_message(chat_id=chat_id, text=text_message)
    if uid and chat_id and text_message:  # Если все необходимые данные присутствуют
        await bot.send_message(chat_id=chat_id, text=text_message)  # Отправка сообщения пользователю
        logging.info(f"Сообщение отправлено пользователю {uid}")  # Логирование отправки сообщения
    else:  # Если какие-то данные отсутствуют
        logging.error("Некорректные данные в сообщении от техподдержки")  # Логирование ошибки

async def main():
    # Запуск проверки почты в фоновом режиме
    asyncio.create_task(check_email())

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)  # Установка уровня логирования INFO
    asyncio.run(main())  # Запуск основной асинхронной функции

