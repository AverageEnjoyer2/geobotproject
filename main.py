import logging

from aiogram import executor, types, Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
import asyncio
import requests
from random import choice

API_TOKEN = "Вставьте токен"


logging.basicConfig(level=logging.INFO)
cities = [["Армавир", "Краснодарский Край"], ["Сальск", "Ростовская область"], ["Обнинск", "Калужская область"], ["Ачинск", "Красноярский край"]]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
waiting_for_answer = False
city = []
proposed_answers = []
chat_id = ""


from aiogram import types

async def set_default_commands(dp):
    await dp.bot.set_my_commands([
        types.BotCommand("start", "Приветствие"),
        types.BotCommand("help", "Помощь"),
        types.BotCommand("play", "Начать игру"),
    ])



@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
   await message.answer('Здравствуйте!')


@dp.message_handler(commands=['help'])
async def start_message(message: types.Message):
   await message.answer('Я покажу карту небольшого города и его окрестностей, а вы попытаетесь угадать его субъект! Начать игру командой play!')

@dp.message_handler(commands=['play'])
async def start_message(message: types.Message):
    global city, cities
    cities = [["Армавир", "Краснодарский Край"], ["Сальск", "Ростовская область"], ["Обнинск", "Калужская область"], ["Ачинск", "Красноярский край"]]
    city = choice(cities)
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode=" \
                       f"{city[0]}&kind=metro&format=json"
    response = requests.get(geocoder_request)
    json_response = response.json()
    coords = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"][
        "Point"]["pos"].split()
    map_request = f"https://static-maps.yandex.ru/1.x/?ll={coords[0]},{coords[1]}&spn=0.2,0.2&l=map"
    response = requests.get(map_request)
    map_file = "map.png"
    with open(map_file, "wb") as file:
        file.write(response.content)
    global proposed_answers
    proposed_answers = [city[1]]
    testcities = cities
    del testcities[testcities.index(city)]
    for i in range(3):
        proposed_answers.append(testcities.pop(testcities.index(choice(testcities)))[1])
    inline_kb = InlineKeyboardMarkup(row_width=2)
    i = 0
    for propregion in proposed_answers:
        i += 1
        inline_kb.add(InlineKeyboardButton(propregion, callback_data=f'btn{i}'))
    print(proposed_answers)
    global waiting_for_answer
    waiting_for_answer = True
    global chat_id
    chat_id = message.chat.id
    with open('map.png', 'rb') as photo:
        await bot.send_photo(chat_id=message.chat.id, photo=photo, reply_markup=inline_kb)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('btn'))
async def process_callback_kb1btn1(callback_query: types.CallbackQuery):
    global waiting_for_answer
    if waiting_for_answer:
        code = int(callback_query.data[-1])
        if proposed_answers[code - 1] == city[1]:
            await bot.send_message(chat_id=chat_id, text='Правильно!')
        else:
            await bot.send_message(chat_id=chat_id, text=f'Неправильно! Правильный субъект - {city[1]}')
        waiting_for_answer = False


if __name__ == '__main__':
   executor.start_polling(dp, skip_updates=True)
