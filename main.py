import logging
import psycopg2
from aiogram import executor, types, Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
import asyncio
import requests
from random import choice
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = "7073227849:AAHQ85zGxsC8Jv4kc27ec7NTCFsAR0p0MiA"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
waiting_for_answer = False
rightansw = []
proposed_answers = []
chat_id = ""
POSTGRES_CONN = "postgres://postgres:S11032008@127rrr.0.0.1:8080/prodtest"
POSTGRES_USERNAME = "postgres"
POSTGRES_PASSWORD = "S11032008"
POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = "8080"
POSTGRES_DATABASE = "postgres"
try:
    connection = psycopg2.connect(user=POSTGRES_CONN.split(":")[1][2:], host=POSTGRES_CONN.split(":")[2].split("@")[1],
                                  port=int(POSTGRES_CONN.split(":")[3].split("/")[0]),
                                  database=POSTGRES_CONN.split(":")[3].split("/")[1],
                                  password=POSTGRES_CONN.split(":")[2].split("@")[0])
except psycopg2.OperationalError:
    connection = psycopg2.connect(user=POSTGRES_USERNAME, host=POSTGRES_HOST,
                                  port=int(POSTGRES_PORT),
                                  database=POSTGRES_DATABASE,
                                  password=POSTGRES_PASSWORD)


class Waitforcity(StatesGroup):
    city = State()
    radius = State()
    final = State()


async def set_default_commands(dp):
    await dp.bot.set_my_commands([
        types.BotCommand("start", "Приветствие"),
        types.BotCommand("help", "Помощь"),
        types.BotCommand("play", "Унадайте город"),
        types.BotCommand("me", "Посмотреть свою статистику"),
        types.BotCommand("playflag", "Угадайте игру по флагу"),
        types.BotCommand("citymap", "Сгенерировать карту окрестностей города или метса")
    ])


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    cur = connection.cursor()
    cur.execute("""SELECT userip FROM useripstats""")
    result = cur.fetchall()
    await message.answer('Здравствуйте!')
    registered = False
    for id in result:
        if str(id[0]) == str(message.from_user.id):
            registered = True
            break
    if not registered:
        cur.execute(f"""INSERT INTO useripstats (id, userip, wins, losses) VALUES
                ('{len(result)}', '{message.from_user.id}','0','0');""")
        connection.commit()


@dp.message_handler(commands=['help'])
async def start_message(message: types.Message):
    await message.answer(
        'Я покажу карту небольшого города и его окрестностей, а вы попытаетесь угадать его субъект! Начать игру командой play!')


@dp.message_handler(commands=['play'])
async def start_message(message: types.Message):
    global rightansw
    cities = [["Армавир", "Краснодарский Край"], ["Сальск", "Ростовская область"], ["Обнинск", "Калужская область"],
              ["Ачинск", "Красноярский край"], ["Стерлитамак", "Республика Башкортостан"],
              ["Златоуст", "Челябинская область"], ["Сызрань", "Самарская область"],
              ["Вятские Поляны", "Кировская область"], ["Камышин", "Волгоградская область"]]
    rightansw = choice(cities)
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode=" \
                       f"{rightansw[0]}&kind=metro&format=json"
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
    proposed_answers = [rightansw[1]]
    testcities = cities
    del testcities[testcities.index(rightansw)]
    for i in range(3):
        proposed_answers.append(testcities.pop(testcities.index(choice(testcities)))[1])
    inline_kb = InlineKeyboardMarkup(row_width=2)
    i = 0
    for propregion in proposed_answers:
        i += 1
        inline_kb.add(InlineKeyboardButton(propregion, callback_data=f'btn{i}'))
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
        if proposed_answers[code - 1] == rightansw[1]:
            cur = connection.cursor()
            cur.execute(f"""SELECT wins FROM useripstats WHERE userip = '{callback_query.from_user.id}'""")
            result = cur.fetchall()
            cur.execute(
                f"""UPDATE useripstats SET wins = '{int(result[0][0]) + 1}' WHERE userip = '{callback_query.from_user.id}'""")
            connection.commit()
            await bot.send_message(chat_id=chat_id, text='Правильно!')
        else:
            cur = connection.cursor()
            cur.execute(f"""SELECT losses FROM useripstats WHERE userip = '{callback_query.from_user.id}'""")
            result = cur.fetchall()
            cur.execute(
                f"""UPDATE useripstats SET losses = '{int(result[0][0]) + 1}' WHERE userip = '{callback_query.from_user.id}'""")
            connection.commit()
            await bot.send_message(chat_id=chat_id, text=f'Неправильно! Правильный ответ - {rightansw[1]}')
        waiting_for_answer = False


@dp.message_handler(commands=['me'])
async def stat_message(message: types.Message):
    cur = connection.cursor()
    cur.execute(f"""SELECT wins, losses FROM useripstats WHERE userip = '{message.from_user.id}'""")
    result = cur.fetchall()
    if not result[0]:
        await message.answer('Вас нет в базе данных!')
    elif int(result[0][1]) == 0:
        await message.answer(f'Похожы вы ещё ни разу не проигрывали! Число ваших побед - {result[0][0]}')
    else:
        await message.answer(
            f'Число ваших побед - {result[0][0]}, Число ваших проигрышей - {result[0][1]}, '
            f'соотношение побед к проигрышам - {round(int(result[0][0]) / int(result[0][1]), 2)}')


@dp.message_handler(commands=['playflag'])
async def flag_message(message: types.Message):
    global rightansw
    countries = [["Guat.png", "Гватемала"], ["CAR.png", "Центральноафриканская республика"],
                 ["Switzerland.png", "Швейцария"], ["Bolivia.png", "Боливия"], ["columb.png", "Колумбия"],
                 ["haiti.png", "Гаити"], ["argentina.png", "Аргентина"], ["cambodia.png", "Камбоджа"],
                 ["india.png", "Индия"]]
    rightansw = choice(countries)
    global proposed_answers
    proposed_answers = [rightansw[1]]
    testcities = countries
    del testcities[testcities.index(rightansw)]
    for i in range(3):
        proposed_answers.append(testcities.pop(testcities.index(choice(testcities)))[1])
    inline_kb = InlineKeyboardMarkup(row_width=2)
    i = 0
    for propregion in proposed_answers:
        i += 1
        inline_kb.add(InlineKeyboardButton(propregion, callback_data=f'btn{i}'))
    global waiting_for_answer
    waiting_for_answer = True
    global chat_id
    chat_id = message.chat.id
    with open(rightansw[0], 'rb') as photo:
        await bot.send_photo(chat_id=message.chat.id, photo=photo, reply_markup=inline_kb)


@dp.message_handler(commands=['citymap'])
async def city_map(message: types.Message):
    await message.answer('Введите город или место, карту окрестностей которого хотите сгенерировать!')
    await Waitforcity.city.set()


@dp.message_handler(state=Waitforcity.city)
async def process_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text

    await Waitforcity.next()
    await message.reply("Насколько отдалённую карту хотите(~0.05-10)?")


def isnumber(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


@dp.message_handler(lambda message: isnumber(message.text), state=Waitforcity.radius)
async def process_radius(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        cit = data['city']
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode=" \
                       f"{cit}&kind=metro&format=json"
    response = requests.get(geocoder_request)
    if response:
        json_response = response.json()
        coords = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"][
            "Point"]["pos"].split()
        map_request = f"https://static-maps.yandex.ru/1.x/?ll={coords[0]},{coords[1]}&spn={message.text},{message.text}&l=map"
        response = requests.get(map_request)
        map_file = "map.png"
        with open(map_file, "wb") as file:
            file.write(response.content)
        global chat_id
        chat_id = message.chat.id
        with open('map.png', 'rb') as photo:
            await bot.send_photo(chat_id=message.chat.id, photo=photo)
    else:
        return await message.reply("Что-то пошло не так!")
    await state.finish()


@dp.message_handler(lambda message: not message.text.isdigit(), state=Waitforcity.radius)
async def process_radius_invalid(message: types.Message):
    return await message.reply("Напиши числом!")


@dp.message_handler(commands=['playindependence'])
async def start_message(message: types.Message):
    global rightansw
    countries = [["15 сентября 1821", "Гондурас"], ["4 июля 1776", "Соединённые Штаты Америки"],
                 ["17 апреля 1982 года", "Канада"], ["7 сентября 1822 года", "Бразилия"],
                 ["20 июля 1810 года", "Колумбия"], ["1 января 1804 года", "Гаити"], ["9 июля 1816 года", "Аргентина"],
                 ["9 ноября 1953 года", "Камбоджа"], ["15 августа 1947 года", "Индия"]]
    rightansw = choice(countries)
    global proposed_answers
    proposed_answers = [rightansw[1]]
    testcities = countries
    del testcities[testcities.index(rightansw)]
    for i in range(3):
        proposed_answers.append(testcities.pop(testcities.index(choice(testcities)))[1])
    inline_kb = InlineKeyboardMarkup(row_width=2)
    i = 0
    for propregion in proposed_answers:
        i += 1
        inline_kb.add(InlineKeyboardButton(propregion, callback_data=f'btn{i}'))
    global waiting_for_answer
    waiting_for_answer = True
    global chat_id
    chat_id = message.chat.id
    await message.reply(rightansw[0], reply_markup=inline_kb)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
