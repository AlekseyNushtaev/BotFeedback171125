from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton

from bot import bot
from config import ADMIN_ID, CHANEL_ID
import logging
import time

logger = logging.getLogger(__name__)

# Создание роутера
router = Router()

# Словарь для отслеживания времени последнего сообщения от пользователей
user_last_message_time = {}


def is_flood(user_id: int, interval: int = 10) -> bool:
    """Проверяет, не слишком ли часто пользователь отправляет сообщения"""
    current_time = time.time()
    last_time = user_last_message_time.get(user_id, 0)

    if current_time - last_time < interval:
        return True

    user_last_message_time[user_id] = current_time
    return False


# Класс для состояний FSM
class Form(StatesGroup):
    normal = State()
    anonymous = State()


# Класс для состояний админа
class AdminForm(StatesGroup):
    waiting_post_text = State()


# Клавиатура для выбора типа отправки
choice_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🙂 Обычный"),
            KeyboardButton(text="🕶 Анонимный")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    # Сбрасываем состояние
    await state.clear()

    # Первое сообщение
    await message.answer(
        "Сюда можно прислать любую новость: <b>текст, фото, видео и аудио.</b>\n\n"
        "💁🏻‍♂️Обязательно напишите адрес, место и время, когда это произошло. Ваши фото и видео будут в 10 раз нагляднее, чем просто текст.\n\n"
        "Пост будет опубликован в канале <b>Vostok Wave • Владивосток и Приморье</b>\n\n",
        parse_mode=ParseMode.HTML
    )

    # Второе сообщение с клавиатурой
    await message.answer(
        "Выберете тип отправки предложений 👇",
        reply_markup=choice_keyboard
    )


# Обработчик команды /post (только для админа)
@router.message(Command("post"))
async def cmd_post(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администратору.")
        return

    await state.set_state(AdminForm.waiting_post_text)
    await message.answer(
        "📝 Пришлите текст сообщения для публикации в канале:",
        reply_markup=ReplyKeyboardRemove()
    )


# Обработчик текста поста от админа
@router.message(AdminForm.waiting_post_text, F.text)
async def process_admin_post(message: Message, state: FSMContext):
    try:
        # Получаем username бота для создания ссылки
        bot_info = await bot.get_me()
        bot_username = bot_info.username

        # Создаем кнопку "Прислать новость"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Прислать новость",
                    url=f"https://t.me/{bot_username}?start=start"
                )]
            ]
        )

        # Отправляем сообщение в канал
        msg = await bot.send_message(
            CHANEL_ID,
            message.text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await bot.pin_chat_message(CHANEL_ID, msg.message_id)

        await message.answer("✅ Сообщение успешно опубликовано в канале!")

    except Exception as e:
        logger.error(f"Ошибка при публикации поста: {e}")
        await message.answer("❌ Произошла ошибка при публикации поста.")

    await state.clear()


# Обработчик кнопки "Обычный"
@router.message(F.text == "🙂 Обычный")
async def normal_mode(message: Message, state: FSMContext):
    await state.set_state(Form.normal)
    await message.answer(
        "💁🏻‍♂️ Если есть <b>фото или видео</b>, то прикрепите их к сообщению\n\n"
        "Расскажите, что произошло?\n\n"
        "Перезапустить бота - команда /start",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )


# Обработчик кнопки "Анонимный"
@router.message(F.text == "🕶 Анонимный")
async def anonymous_mode(message: Message, state: FSMContext):
    await state.set_state(Form.anonymous)
    await message.answer(
        "🕶 Если есть <b>фото или видео</b>, то прикрепите их к сообщению\n\n"
        "Расскажите, что произошло?\n\n"
        "Перезапустить бота - команда /start",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )


# Обработчик для обычных сообщений (текст)
@router.message(Form.normal, F.text)
async def handle_normal_text(message: Message, state: FSMContext):
    # Проверка на флуд
    if is_flood(message.from_user.id):
        await message.answer("❌ Слишком часто! Подождите 10 секунд перед следующим сообщением.")
        return

    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

    # Отправляем уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"Пользователь {user_info} отправил <b>ОБЫЧНОЕ</b> сообщение",
        parse_mode=ParseMode.HTML
    )

    # Пересылаем сообщение админу
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    await message.answer("✅ Ваше сообщение отправлено!")
    await state.clear()


# Обработчик для анонимных сообщений (текст)
@router.message(Form.anonymous, F.text)
async def handle_anonymous_text(message: Message, state: FSMContext):
    # Проверка на флуд
    if is_flood(message.from_user.id):
        await message.answer("❌ Слишком часто! Подождите 10 секунд перед следующим сообщением.")
        return

    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

    # Отправляем уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"Пользователь {user_info} отправил 🕶 <b>АНОНИМНОЕ</b> сообщение",
        parse_mode=ParseMode.HTML
    )

    # Пересылаем сообщение админу
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    await message.answer("✅ Ваше анонимное сообщение отправлено!")
    await state.clear()


# Обработчик для медиа-сообщений (фото, видео, аудио) в обычном режиме
@router.message(Form.normal, F.content_type.in_({'photo', 'video', 'audio'}))
async def handle_normal_media(message: Message, state: FSMContext):
    # Проверка на флуд
    if is_flood(message.from_user.id):
        await message.answer("❌ Слишком часто! Подождите 10 секунд перед следующим сообщением.")
        return

    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

    # Отправляем уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"Пользователь {user_info} отправил <b>ОБЫЧНОЕ</b> сообщение",
        parse_mode=ParseMode.HTML
    )

    # Пересылаем медиа админу
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    await message.answer("✅ Ваше сообщение отправлено!")
    await state.clear()


# Обработчик для медиа-сообщений (фото, видео, аудио) в анонимном режиме
@router.message(Form.anonymous, F.content_type.in_({'photo', 'video', 'audio'}))
async def handle_anonymous_media(message: Message, state: FSMContext):
    # Проверка на флуд
    if is_flood(message.from_user.id):
        await message.answer("❌ Слишком часто! Подождите 10 секунд перед следующим сообщением.")
        return

    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

    # Отправляем уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"Пользователь {user_info} отправил 🕶 <b>АНОНИМНОЕ</b> сообщение",
        parse_mode=ParseMode.HTML
    )

    # Пересылаем медиа админу
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    await message.answer("✅ Ваше анонимное сообщение отправлено!")
    await state.clear()


# Обработчик для любых сообщений вне состояний (если пользователь просто что-то отправил)
@router.message(StateFilter(None))
async def handle_other_messages(message: Message):
    await message.answer(
        "Для начала работы с ботом используйте команду /start",
        reply_markup=ReplyKeyboardRemove()
    )
