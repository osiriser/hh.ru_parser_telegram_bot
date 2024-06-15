import asyncio
import csv
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Callable

import emoji
import selenium
from aiogram import Bot, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.types import ChatActions, InputFile, ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.message import ContentType
from aiogram.utils import executor, exceptions
from aiogram.utils.markdown import bold, code, italic, text
from bs4 import BeautifulSoup as bs
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import InvalidArgumentException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


URL_TEMPLATE = (
    'https://spb.hh.ru/search/vacancy?area=2&clusters=true&'
    'enable_snippets=true&experience=noExperience&'
    'ored_clusters=true&text=python+django+%7C+python&'
    'order_by=publication_time&hhtmFrom=vacancy_search_list'
)
FILE_NAME = 'result.csv'
LOG_FILE_NAME = 'job_parser.log'
TOKEN = os.getenv('TG_TOKEN')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    filename=LOG_FILE_NAME,
    maxBytes=5000000,
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def parse(url: str) -> list:
    result_list: list = []

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except selenium.common.exceptions.WebDriverException as e:
        logger.error(e)
        ser = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=ser, options=chrome_options)
    else:
        logger.info('Chrome driver started without errors.')

    try:
        driver.get(url)
    except InvalidArgumentException:
        logger.critical('Wrong URL given')
        driver.close()
        return []

    html = driver.page_source

    soup = bs(html, 'html.parser')
    vacancies_names = soup.find_all('a', attrs={'data-qa': 'serp-item__title'})
    vacancies_employers = soup.find_all(
        'a',
        attrs={'data-qa': 'vacancy-serp__vacancy-employer'}
    )
    vacancies_descriptions = soup.find_all(
        'div',
        attrs={'data-qa': 'vacancy-serp__vacancy_snippet_responsibility'}
    )
    vacancies_requirements = soup.find_all(
        'div',
        attrs={'data-qa': 'vacancy-serp__vacancy_snippet_requirement'}
    )
    for name, employer, description, requirements in zip(
        vacancies_names,
        vacancies_employers,
        vacancies_descriptions,
        vacancies_requirements
    ):
        result_list.append({
            'Vacancy': name.text,
            'Employer': employer.text,
            'Description': description.text,
            'Requirements': requirements.text,
            'Link': name['href']
        })
    driver.close()
    return result_list


def create_csv_file(data: list, filename: str) -> None:
    with open(filename, 'w', newline='') as csvfile:
        try:
            fieldnames = data[0].keys()
        except IndexError:
            logger.error('Wrong data given to create csv')
            return -1
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def parse_to_csv(url: str = URL_TEMPLATE, filename: str = FILE_NAME) -> None:
    data = parse(url)
    create_csv_file(data, filename)


def tg_make_send_bot(
    token: str,
    func_to_exec: Callable,
    filename: str
) -> None:
    if not token:
        logger.critical('Telegram token not found. Program terminated.')
        os._exit(0)
    try:
        bot = Bot(token=token)
    except exceptions.ValidationError:
        logger.critical('Telegram token validation error.')
        os._exit(0)

    dp = Dispatcher(bot)
    dp.middleware.setup(LoggingMiddleware())
    button_make_file = InlineKeyboardButton(
        emoji.emojize('Make file :writing_hand_light_skin_tone:'),
        callback_data='make_file'
    )
    button_download_file = InlineKeyboardButton(
        emoji.emojize('Download file :envelope_with_arrow:'),
        callback_data='download_file'
    )
    button_help = InlineKeyboardButton(
        emoji.emojize('Help :red_question_mark:'),
        callback_data='help'
    )
    markup_kb = InlineKeyboardMarkup(row_width=2).row(
        button_make_file,
        button_download_file
    ).add(button_help)

    @dp.callback_query_handler(lambda c: c.data)
    async def process_callback_kb(callback_query: types.CallbackQuery):
        if callback_query.data == 'help':
            await process_help_command(
                callback_query.message
            )
            await bot.answer_callback_query(callback_query.id)
        if callback_query.data == 'make_file':
            await process_make_file_command(
                callback_query.message
            )
            await bot.answer_callback_query(callback_query.id, text='Done')
        if callback_query.data == 'download_file':
            await process_download_file_command(
                callback_query.message
            )
            await bot.answer_callback_query(callback_query.id, text='Done')

    @dp.message_handler(commands=['start'])
    async def process_start_command(message: types.Message):
        await message.reply(
            'Bot started.\nType /help for info.',
            reply_markup=markup_kb
        )

    @dp.message_handler(commands=['help'])
    async def process_help_command(message: types.Message):
        msg = text(
            bold('Allowed commands:'),
            '/makefile', '/downloadfile',
            sep='\n'
        )
        await bot.send_message(
            message.chat.id,
            text=msg,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=markup_kb
            )

    @dp.message_handler(commands=['downloadfile'])
    async def process_download_file_command(message: types.Message):
        await bot.send_chat_action(
            message.chat.id,
            ChatActions.UPLOAD_DOCUMENT
        )
        await asyncio.sleep(1)
        try:
            file = InputFile(filename)
        except FileNotFoundError:
            logger.error('File to send not found')
            await bot.send_message(message.chat.id, 'Make file first.')
        else:
            await bot.send_document(
                message.chat.id,
                file,
                caption='file ready'
            )

    @dp.message_handler(commands=['makefile'])
    async def process_make_file_command(message: types.Message):
        func_to_exec()
        await asyncio.sleep(1)
        await bot.send_message(message.chat.id, 'Done')

    @dp.message_handler(commands=['log'])
    async def process_get_log_file(message: types.Message):
        user_id = message.from_user.id
        await bot.send_chat_action(user_id, ChatActions.UPLOAD_DOCUMENT)
        await bot.send_document(
            user_id,
            InputFile(LOG_FILE_NAME),
            caption='log file'
        )

    @dp.message_handler()
    async def echo_message(msg):
        await bot.send_message(msg.from_user.id, msg.text)

    @dp.message_handler(content_types=ContentType.ANY)
    async def unknown_message(msg: types.Message):
        message_text = text(
            emoji.emojize('Я не знаю, что с этим делать :eyes:'),
            italic('\nЯ просто напомню,'), 'что есть',
            code('команда'), '/help',
        )
        await msg.reply(message_text, parse_mode=ParseMode.MARKDOWN)

    executor.start_polling(dp)


if __name__ == '__main__':
    tg_make_send_bot(TOKEN, parse_to_csv, FILE_NAME)
