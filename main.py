#!/usr/bin/env python3
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ============ ОБХОД ДЛЯ RAILWAY ============
# Это создаст заглушку веб-сервера, чтобы Railway не падал
try:
    from aiohttp import web
    
    async def handle(request):
        return web.Response(text="Bot is running")
    
    async def start_web():
        app = web.Application()
        app.router.add_get("/", handle)
        app.router.add_get("/health", handle)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"✅ Web server started on port {port}")
    
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
except ImportError:
    print("❌ aiohttp not installed, continuing without web server")
except Exception as e:
    print(f"❌ Failed to start web server: {e}")
# ============================================

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
DATA_FILE = "/data/bot_data.json"
# ===================================

import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ============ НАСТРОЙКИ ============
# ⚠️ НЕ ВСТАВЛЯЙ ТОКЕН СЮДА! Он будет в переменных окружения Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# ⚠️ ВАЖНО! Путь к файлу данных — на Volume, чтобы не пропадал!
DATA_FILE = "/data/bot_data.json"  # Railway Volume монтируется сюда
# ===================================

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")
if not ADMIN_ID:
    raise ValueError("❌ ADMIN_ID не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ============
storage = {}
groups = {}

# ============ ЗАГРУЗКА/СОХРАНЕНИЕ (РАБОТАЕТ С VOLUME) ============
def load_data():
    global storage, groups
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            storage = {int(k): v for k, v in data.get('storage', {}).items()}
            groups_data = data.get('groups', {})
            if groups_data:
                groups = {int(k): v for k, v in groups_data.items()}
            else:
                groups = {}
            print(f"📂 Загружено: {len(storage)} связей, {len(groups)} групп из {DATA_FILE}")
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            storage, groups = {}, {}
    else:
        print(f"📁 Файл {DATA_FILE} не найден, создаём новый при сохранении")
        storage, groups = {}, {}

def save_data():
    global storage, groups
    try:
        # Создаём директорию /data, если её нет
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        data = {
            'storage': {str(k): v for k, v in storage.items()},
            'groups': groups
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены в {DATA_FILE}")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")

# Загружаем данные при старте
load_data()

# Автосохранение
async def auto_save():
    save_data()

# ============ ПРОВЕРКА НА ЛИЧНЫЕ СООБЩЕНИЯ ============
async def check_private_chat(message: Message):
    if message.chat.type != "private":
        await message.answer("❌ Бот работает только в личных сообщениях!")
        return False
    return True

# ============ ФИЛЬТР ГРУПП ============
@dp.message(F.chat.type != "private")
async def group_chat_handler(message: Message):
    await message.answer("❌ Бот работает только в личных сообщениях. Напишите мне в личку.")

# ============ СОСТОЯНИЯ ============
class GroupStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_link = State()
    waiting_for_description = State()

# ============ КОМАНДЫ АДМИНА ============
@dp.message(Command("addgroup"))
async def cmd_add_group(message: Message, state: FSMContext):
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Эта команда только для администратора")
        return
    await message.answer("✏️ Введите название группы:")
    await state.set_state(GroupStates.waiting_for_title)

@dp.message(Command("listgroups"))
async def cmd_list_groups(message: Message):
    global groups
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Эта команда только для администратора")
        return
    if not groups:
        await message.answer("📭 Список групп пуст. Добавьте группу через /addgroup")
        return
    text = "📋 Список доступных групп:\n\n"
    for group_id, group in groups.items():
        text += f"🆔 ID: {group_id}\n📌 Название: {group['title']}\n🔗 Ссылка: {group['invite_link']}\n"
        if group['description']:
            text += f"📝 Описание: {group['description']}\n"
        text += "─" * 20 + "\n"
    await message.answer(text)

@dp.message(Command("delgroup"))
async def cmd_del_group(message: Message):
    global groups
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Эта команда только для администратора")
        return
    if not groups:
        await message.answer("📭 Список групп пуст")
        return
    text = "🗑 Для удаления группы отправьте:\n/delgroup ID\n\nДоступные группы:\n"
    for group_id, group in groups.items():
        text += f"ID {group_id}: {group['title']}\n"
    await message.answer(text)

@dp.message(F.text.startswith("/delgroup"))
async def process_del_group(message: Message):
    global groups
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        return
    try:
        group_id = int(message.text.split()[1])
        if group_id in groups:
            group_title = groups[group_id]['title']
            del groups[group_id]
            await message.answer(f"✅ Группа '{group_title}' удалена")
            await auto_save()
        else:
            await message.answer("❌ Группа с таким ID не найдена")
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /delgroup ID")

@dp.message(GroupStates.waiting_for_title)
async def process_group_title(message: Message, state: FSMContext):
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(title=message.text)
    await message.answer("🔗 Введите ссылку-приглашение в группу:")
    await state.set_state(GroupStates.waiting_for_link)

@dp.message(GroupStates.waiting_for_link)
async def process_group_link(message: Message, state: FSMContext):
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(link=message.text)
    await message.answer("📝 Введите описание группы (или отправьте '-' чтобы пропустить):")
    await state.set_state(GroupStates.waiting_for_description)

@dp.message(GroupStates.waiting_for_description)
async def process_group_description(message: Message, state: FSMContext):
    global groups
    if not await check_private_chat(message):
        return
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    title = data['title']
    link = data['link']
    description = message.text if message.text != '-' else ''
    
    if groups:
        group_id = max(groups.keys()) + 1
    else:
        group_id = 1
    
    groups[group_id] = {
        'title': title,
        'invite_link': link,
        'description': description
    }
    
    await message.answer(f"✅ Группа успешно добавлена!\n\nID: {group_id}\nНазвание: {title}\nСсылка: {link}\nОписание: {description or 'отсутствует'}")
    await auto_save()
    await state.clear()

# ============ ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ============
@dp.message(Command("groups"))
async def cmd_show_groups(message: Message):
    global groups
    if not await check_private_chat(message):
        return
    if not groups:
        await message.answer("📭 На данный момент нет доступных групп для вступления")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for group_id, group in groups.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"📢 {group['title']}", callback_data=f"group_{group_id}")
        ])
    
    await message.answer("👥 Доступные группы для вступления:\n\nВыберите группу, чтобы получить ссылку-приглашение:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("group_"))
async def process_group_selection(callback: CallbackQuery):
    global groups
    if callback.message.chat.type != "private":
        await callback.answer("❌ Эта функция работает только в личных сообщениях", show_alert=True)
        return
    
    group_id = int(callback.data.split("_")[1])
    group = groups.get(group_id)
    
    if not group:
        await callback.message.edit_text("❌ Группа больше не доступна")
        await callback.answer()
        return
    
    text = f"📢 <b>{group['title']}</b>\n\n"
    if group['description']:
        text += f"📝 <b>Описание:</b>\n{group['description']}\n\n"
    text += f"🔗 <b>Ссылка для вступления:</b>\n{group['invite_link']}"
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

# ============ ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ ТИПА СООБЩЕНИЯ ============
def get_message_type(message: Message):
    if message.text:
        return "text", message.text
    elif message.photo:
        return "photo", message.photo[-1].file_id
    elif message.video:
        return "video", message.video.file_id
    elif message.document:
        return "document", message.document.file_id
    elif message.audio:
        return "audio", message.audio.file_id
    elif message.voice:
        return "voice", message.voice.file_id
    elif message.sticker:
        return "sticker", message.sticker.file_id
    elif message.animation:
        return "animation", message.animation.file_id
    elif message.video_note:
        return "video_note", message.video_note.file_id
    elif message.contact:
        return "contact", message.contact
    elif message.location:
        return "location", message.location
    elif message.venue:
        return "venue", message.venue
    elif message.poll:
        return "poll", message.poll
    elif message.dice:
        return "dice", message.dice
    else:
        return "unknown", None

# ============ ПЕРЕСЫЛКА АДМИНУ ============
async def forward_to_admin(message: Message, user_id: int, user_fullname: str, username: str):
    msg_type, content = get_message_type(message)
    caption = f"💬 Сообщение от {user_fullname} (@{username}) (ID: {user_id})"
    sent_messages = []
    
    try:
        if msg_type == "text":
            sent_msg = await bot.send_message(ADMIN_ID, f"{caption}:\n\n{content}")
            sent_messages.append(sent_msg)
        elif msg_type == "photo":
            sent_msg = await bot.send_photo(ADMIN_ID, photo=content, caption=f"{caption}\n\n{message.caption or ''}")
            sent_messages.append(sent_msg)
        elif msg_type == "video":
            sent_msg = await bot.send_video(ADMIN_ID, video=content, caption=f"{caption}\n\n{message.caption or ''}")
            sent_messages.append(sent_msg)
        elif msg_type == "document":
            sent_msg = await bot.send_document(ADMIN_ID, document=content, caption=f"{caption}\n\n{message.caption or ''}")
            sent_messages.append(sent_msg)
        elif msg_type == "audio":
            sent_msg = await bot.send_audio(ADMIN_ID, audio=content, caption=f"{caption}\n\n{message.caption or ''}")
            sent_messages.append(sent_msg)
        elif msg_type == "voice":
            sent_msg = await bot.send_voice(ADMIN_ID, voice=content, caption=f"{caption}\n\n{message.caption or ''}")
            sent_messages.append(sent_msg)
        elif msg_type == "sticker":
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n📦 Отправил стикер")
            sent_messages.append(info_msg)
            sent_msg = await bot.send_sticker(ADMIN_ID, sticker=content)
            sent_messages.append(sent_msg)
        elif msg_type == "animation":
            sent_msg = await bot.send_animation(ADMIN_ID, animation=content, caption=f"{caption}\n\n{message.caption or ''}")
            sent_messages.append(sent_msg)
        elif msg_type == "video_note":
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n📦 Отправил кружок")
            sent_messages.append(info_msg)
            sent_msg = await bot.send_video_note(ADMIN_ID, video_note=content)
            sent_messages.append(sent_msg)
        elif msg_type == "contact":
            sent_msg = await bot.send_contact(ADMIN_ID, phone_number=content.phone_number, first_name=content.first_name, last_name=content.last_name)
            sent_messages.append(sent_msg)
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n📦 Отправил контакт")
            sent_messages.append(info_msg)
        elif msg_type == "location":
            sent_msg = await bot.send_location(ADMIN_ID, latitude=content.latitude, longitude=content.longitude)
            sent_messages.append(sent_msg)
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n📍 Отправил геолокацию")
            sent_messages.append(info_msg)
        elif msg_type == "venue":
            sent_msg = await bot.send_venue(ADMIN_ID, latitude=content.location.latitude, longitude=content.location.longitude, title=content.title, address=content.address)
            sent_messages.append(sent_msg)
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n📍 Отправил место")
            sent_messages.append(info_msg)
        elif msg_type == "poll":
            sent_msg = await bot.send_poll(ADMIN_ID, question=content.question, options=[opt.text for opt in content.options], is_anonymous=content.is_anonymous)
            sent_messages.append(sent_msg)
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n📊 Отправил опрос")
            sent_messages.append(info_msg)
        elif msg_type == "dice":
            sent_msg = await bot.send_dice(ADMIN_ID, emoji=content.emoji)
            sent_messages.append(sent_msg)
            info_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n🎲 Отправил {content.emoji}")
            sent_messages.append(info_msg)
        else:
            sent_msg = await bot.send_message(ADMIN_ID, f"{caption}\n\n❌ Неподдерживаемый тип сообщения")
            sent_messages.append(sent_msg)
        
        return sent_messages
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await bot.send_message(ADMIN_ID, f"{caption}\n\n❌ Ошибка: {e}")
        return []

# ============ ОТВЕТ ПОЛЬЗОВАТЕЛЮ ============
async def reply_to_user(message: Message, target_user: int):
    msg_type, content = get_message_type(message)
    
    try:
        if msg_type == "text":
            await bot.send_message(chat_id=target_user, text=f"📨 Ответ администратора:\n\n{content}")
        elif msg_type == "photo":
            await bot.send_photo(chat_id=target_user, photo=content, caption=f"📨 Ответ администратора:\n\n{message.caption or ''}")
        elif msg_type == "video":
            await bot.send_video(chat_id=target_user, video=content, caption=f"📨 Ответ администратора:\n\n{message.caption or ''}")
        elif msg_type == "document":
            await bot.send_document(chat_id=target_user, document=content, caption=f"📨 Ответ администратора:\n\n{message.caption or ''}")
        elif msg_type == "audio":
            await bot.send_audio(chat_id=target_user, audio=content, caption=f"📨 Ответ администратора:\n\n{message.caption or ''}")
        elif msg_type == "voice":
            await bot.send_voice(chat_id=target_user, voice=content, caption=f"📨 Ответ администратора:\n\n{message.caption or ''}")
        elif msg_type == "sticker":
            await bot.send_sticker(chat_id=target_user, sticker=content)
            if message.caption:
                await bot.send_message(chat_id=target_user, text=f"📨 Ответ администратора:\n\n{message.caption}")
        elif msg_type == "animation":
            await bot.send_animation(chat_id=target_user, animation=content, caption=f"📨 Ответ администратора:\n\n{message.caption or ''}")
        elif msg_type == "video_note":
            await bot.send_video_note(chat_id=target_user, video_note=content)
            if message.caption:
                await bot.send_message(chat_id=target_user, text=f"📨 Ответ администратора:\n\n{message.caption}")
        elif msg_type == "contact":
            await bot.send_contact(chat_id=target_user, phone_number=content.phone_number, first_name=content.first_name, last_name=content.last_name)
        elif msg_type == "location":
            await bot.send_location(chat_id=target_user, latitude=content.latitude, longitude=content.longitude)
        elif msg_type == "venue":
            await bot.send_venue(chat_id=target_user, latitude=content.location.latitude, longitude=content.location.longitude, title=content.title, address=content.address)
        elif msg_type == "poll":
            await bot.send_poll(chat_id=target_user, question=content.question, options=[opt.text for opt in content.options], is_anonymous=content.is_anonymous)
        elif msg_type == "dice":
            await bot.send_dice(chat_id=target_user, emoji=content.emoji)
        else:
            await bot.send_message(chat_id=target_user, text="📨 Ответ администратора:\n\n[Сообщение не может быть отображено]")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка ответа: {e}")
        raise e

# ============ ОСНОВНАЯ ЛОГИКА ============
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not await check_private_chat(message):
        return
    
    welcome_text = (
        "👋 Добро пожаловать!\n\n"
        "📝 <b>Основные команды:</b>\n"
        "• Просто напишите сообщение - связь с администратором\n"
        "• /groups - посмотреть доступные группы\n\n"
        "👑 <b>Команды администратора:</b>\n"
        "• /addgroup - добавить новую группу\n"
        "• /listgroups - список всех групп\n"
        "• /delgroup - удалить группу\n\n"
        "📦 <b>Поддерживаются все типы сообщений!</b>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message()
async def handle_all_messages(message: Message):
    global storage, groups
    
    if not await check_private_chat(message):
        return
    
    user_id = message.from_user.id
    
    # АДМИН
    if user_id == ADMIN_ID:
        if message.reply_to_message:
            original_msg_id = message.reply_to_message.message_id
            target_user = storage.get(original_msg_id)
            
            if target_user:
                try:
                    await reply_to_user(message, target_user)
                    await message.reply("✅ Ответ отправлен!")
                    print(f"✓ Ответ отправлен пользователю {target_user}")
                except Exception as e:
                    await message.reply(f"❌ Ошибка: {e}")
                    print(f"✗ Ошибка отправки: {e}")
            else:
                await message.reply("❌ Не найден пользователь. Отвечайте на сообщение, пересланное от пользователя!")
        return
    
    # ПОЛЬЗОВАТЕЛЬ
    keyboard = None
    if groups:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Доступные группы", callback_data="show_groups_menu")]
        ])
    
    username = message.from_user.username or "нет юзернейма"
    user_fullname = message.from_user.full_name
    
    sent_messages = await forward_to_admin(message, user_id, user_fullname, username)
    
    for sent_msg in sent_messages:
        if sent_msg:
            storage[sent_msg.message_id] = user_id
            print(f"🔗 Связь: {sent_msg.message_id} -> {user_id}")
    
    msg_type, _ = get_message_type(message)
    confirm_text = "✅ Сообщение доставлено администратору!"
    
    if msg_type == "sticker":
        confirm_text = "✅ Стикер доставлен администратору!"
    elif msg_type == "video_note":
        confirm_text = "✅ Кружок доставлен администратору!"
    elif msg_type == "voice":
        confirm_text = "✅ Голосовое сообщение доставлено администратору!"
    elif msg_type == "animation":
        confirm_text = "✅ GIF доставлен администратору!"
    
    if groups:
        confirm_text += "\n\n👥 Также вы можете вступить в наши группы:"
        await message.answer(confirm_text, reply_markup=keyboard)
    else:
        await message.answer(confirm_text)
    
    if len(storage) > 1000:
        storage_keys = sorted(storage.keys())[-500:]
        storage = {k: storage[k] for k in storage_keys}
    
    await auto_save()
    
    print(f"\n--- Новое сообщение ---")
    print(f"От: {user_id} ({user_fullname})")
    print(f"Тип: {msg_type}")
    print(f"Сообщений: {len(sent_messages)}")
    print(f"Всего связей: {len(storage)}")
    print(f"Всего групп: {len(groups)}")
    print("----------------------\n")

@dp.callback_query(F.data == "show_groups_menu")
async def show_groups_menu(callback: CallbackQuery):
    if callback.message.chat.type != "private":
        await callback.answer("", show_alert=True)
        return
    await cmd_show_groups(callback.message)
    await callback.answer()

# ============ ЗАПУСК ============
async def main():
    print("="*50)
    print("🤖 БОТ ЗАПУЩЕН НА RAILWAY!")
    print(f"👑 Администратор: {ADMIN_ID}")
    print(f"📁 Файл данных: {DATA_FILE}")
    print(f"💾 Загружено: {len(storage)} связей, {len(groups)} групп")
    print("="*50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())