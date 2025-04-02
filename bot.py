import re
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.fsm import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# تنظیمات تلگرام
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# تنظیمات FSM
class Form(StatesGroup):
    waiting_for_thread_choice = State()

# تابع استخراج آیدی توییت از لینک
def extract_tweet_id(url):
    match = re.search(r"twitter\.com/.+/status/(\d+)", url)
    return match.group(1) if match else None

# دریافت داده‌های توییت از TwExtract
def get_tweet_data(tweet_url):
    api_url = f"https://twextract.xyz/api/extract?url={tweet_url}"
    response = requests.get(api_url)

    if response.status_code == 200:
        return response.json()
    return None

# تابع بررسی پاسخ‌های توییت برای شناسایی رشته توییت
def is_thread(tweet_data):
    if 'replies' in tweet_data and tweet_data['replies'] > 0:
        return True
    return False

# پردازش پیام‌های حاوی لینک توییتر
@dp.message_handler(lambda message: "twitter.com" in message.text)
async def fetch_tweet(message: types.Message):
    tweet_id = extract_tweet_id(message.text)

    if not tweet_id:
        await message.reply("❌ لینک توییتر نامعتبر است.")
        return

    # دریافت داده‌ها از TwExtract
    tweet_data = get_tweet_data(message.text)

    if not tweet_data:
        await message.reply("⚠️ خطا در دریافت توییت. لطفاً بعداً امتحان کنید.")
        return

    # بررسی اینکه توییت بخشی از رشته توییت است یا نه
    if is_thread(tweet_data):
        # از کاربر می‌پرسیم که آیا می‌خواهد رشته توییت را دریافت کند یا نه
        await message.reply(
            "این توییت بخشی از یک رشته توییت است. آیا می‌خواهید تمام توییت‌های این رشته را دریافت کنید؟ (بله/خیر)"
        )

        # ذخیره وضعیت درخواست در حافظه
        await Form.waiting_for_thread_choice.set()
        await state.update_data(tweet_url=message.text)  # ذخیره لینک توییت
        return

    # اگر توییت فقط یک توییت ساده باشد
    tweet_text = tweet_data.get("text", "متن یافت نشد.")
    await message.reply(f"📢 **توییت:**\n\n{tweet_text}", parse_mode="Markdown")

    # ارسال عکس‌ها
    media_urls = tweet_data.get("media", {}).get("photo", [])
    for media_url in media_urls:
        await bot.send_photo(message.chat.id, media_url)

    # ارسال ویدیوها
    video_urls = tweet_data.get("media", {}).get("video", [])
    for video_url in video_urls:
        await bot.send_video(message.chat.id, video_url)

# پردازش پاسخ‌های کاربر به سوال "آیا می‌خواهید رشته توییت را دریافت کنید؟"
@dp.message_handler(state=Form.waiting_for_thread_choice)
async def handle_thread_choice(message: types.Message, state: FSMContext):
    if message.text.lower() == "بله":
        user_data = await state.get_data()
        tweet_url = user_data['tweet_url']  # دریافت لینک توییت اصلی
        # دریافت تمام توییت‌ها در رشته
        tweet_data = get_tweet_data(tweet_url)
        
        # ارسال توییت‌ها
        for tweet in tweet_data.get('thread', []):
            tweet_text = tweet['text']
            await message.reply(f"📢 **توییت:**\n\n{tweet_text}", parse_mode="Markdown")

            # ارسال عکس‌ها
            media_urls = tweet.get("media", {}).get("photo", [])
            for media_url in media_urls:
                await bot.send_photo(message.chat.id, media_url)

            # ارسال ویدیوها
            video_urls = tweet.get("media", {}).get("video", [])
            for video_url in video_urls:
                await bot.send_video(message.chat.id, video_url)
    elif message.text.lower() == "خیر":
        await message.reply("❌ از ارسال رشته توییت خودداری شد.")
    else:
        await message.reply("لطفاً فقط `بله` یا `خیر` بنویسید.")

    # پس از اتمام، وضعیت را پاک می‌کنیم
    await state.finish()

# اجرای ربات
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
