import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import (
    TOKEN, SERVER, EMAIL_PASSWORD, SUPPORT_EMAIL, BOT_EMAIL, PORT
)
