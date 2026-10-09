import logging, math, os, sqlite3
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonCommands, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DATABASE_PATH", "owa.db")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("owa")

def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS journeys (
            user_id INTEGER PRIMARY KEY, stop_id INTEGER NOT NULL,
            a1000 INTEGER DEFAULT 0, a500 INTEGER DEFAULT 0,
            a150 INTEGER DEFAULT 0, arrived INTEGER DEFAULT 0)""")

def distance_m(a, b, c, d):
    r=6371000
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(min(1,math.sqrt(x)))

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚌 Start journey", callback_data="journey"),
         InlineKeyboardButton("📍 Add a bus stop", callback_data="add")],
        [InlineKeyboardButton("⭐ My saved stops", callback_data="stops"),
         InlineKeyboardButton("🛑 End journey", callback_data="end")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

async def setup_menu(app):
    await app.bot.set_my_commands([
        BotCommand("start","Bot main menu"),
        BotCommand("journey","Start a journey"),
        BotCommand("addstop","Save a bus stop"),
        BotCommand("stops","My saved bus stops"),
        BotCommand("stop","End current journey"),
        BotCommand("help","How to use OWA!")
    ])
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text(
        "OWA! 🚌😂\n\nYour Lagos bus-stop companion. No miss your stop again!\n\nWetin we dey do today?",
        reply_markup=menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "1. Add a stop and share its map pin.\n"
        "2. Start a journey and choose that stop.\n"
        "3. Share Telegram LIVE LOCATION while travelling.\n"
        "I'll alert you at about 1 km, 500 m and 150 m. These are straight-line GPS distances, not road distances.",
        reply_markup=menu())

async def addstop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["want_name"] = True
    context.user_data.pop("want_pin", None)
    await update.effective_message.reply_text("📍 What should we call this bus stop? Send its name.")

async def show_stops(context, chat_id, user_id, journey=False):
    with connect() as c:
        rows=c.execute("SELECT id,name FROM stops WHERE user_id=? ORDER BY name",(user_id,)).fetchall()
    if not rows:
        await context.bot.send_message(chat_id,"No saved stops yet. Tap 📍 Add a bus stop first.",reply_markup=menu())
        return
    buttons=[]
    for row in rows:
        buttons.append([InlineKeyboardButton("🚌 "+row["name"],callback_data=("go:" if journey else "info:")+str(row["id"]))])
    buttons.append([InlineKeyboardButton("➕ Add a bus stop",callback_data="add")])
    await context.bot.send_message(chat_id,"Choose a stop:" if journey else "⭐ Your saved stops:",reply_markup=InlineKeyboardMarkup(buttons))

async def journey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stops(context,update.effective_chat.id,update.effective_user.id,True)

async def stops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stops(context,update.effective_chat.id,update.effective_user.id)

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with connect() as c: c.execute("DELETE FROM journeys WHERE user_id=?",(update.effective_user.id,))
    await update.effective_message.reply_text("Journey ended. Safe travels, my guy! 🚌",reply_markup=menu())

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    data=q.data
    if data=="home":
        await q.message.reply_text("OWA! 🚌\nWetin we dey do today?",reply_markup=menu())
    elif data=="journey":
        await show_stops(context,q.message.chat_id,q.from_user.id,True)
    elif data=="stops":
        await show_stops(context,q.message.chat_id,q.from_user.id)
    elif data=="add":
        context.user_data["want_name"]=True
        context.user_data.pop("want_pin",None)
        await q.message.reply_text("📍 What should we call this bus stop? Send its name.")
    elif data=="end":
        with connect() as c: c.execute("DELETE FROM journeys WHERE user_id=?",(q.from_user.id,))
        await q.message.reply_text("Journey ended. Safe travels, my guy! 🚌",reply_markup=menu())
    elif data=="help":
        await q.message.reply_text("Add a stop, choose it with Start journey, then share Telegram Live Location during the trip. Alerts use straight-line GPS distance.",reply_markup=menu())
    elif data.startswith("go:"):
        sid=int(data.split(":")[1])
        with connect() as c:
            row=c.execute("SELECT name FROM stops WHERE id=? AND user_id=?",(sid,q.from_user.id)).fetchone()
            if row:
                c.execute("""INSERT INTO journeys(user_id,stop_id) VALUES(?,?)
                    ON CONFLICT(user_id) DO UPDATE SET stop_id=excluded.stop_id,
                    a1000=0,a500=0,a150=0,arrived=0""",(q.from_user.id,sid))
        if row:
            await q.message.reply_text("Destination set: "+row["name"]+" 📍\nNow tap 📎 → Location → Share Live Location. Keep it active during your trip.",reply_markup=menu())
    elif data.startswith("info:"):
        sid=int(data.split(":")[1])
        with connect() as c:
            row=c.execute("SELECT name,lat,lon FROM stops WHERE id=? AND user_id=?",(sid,q.from_user.id)).fetchone()
        if row:
            await q.message.reply_text(f"📍 {row['name']}\n{row['lat']:.6f}, {row['lon']:.6f}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚌 Go here",callback_data=f"go:{sid}"),
                InlineKeyboardButton("🗑 Delete",callback_data=f"del:{sid}")]]))
    elif data.startswith("del:"):
        sid=int(data.split(":")[1])
        with connect() as c:
            c.execute("DELETE FROM stops WHERE id=? AND user_id=?",(sid,q.from_user.id))
            c.execute("DELETE FROM journeys WHERE user_id=? AND stop_id=?",(q.from_user.id,sid))
        await q.message.reply_text("Stop deleted.",reply_markup=menu())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg=update.effective_message
    if context.user_data.get("want_name"):
        name=(msg.text or "").strip()
        if not name or len(name)>80:
            await msg.reply_text("Send a stop name up to 80 characters."); return
        context.user_data["pending_name"]=name
        context.user_data.pop("want_name",None)
        context.user_data["want_pin"]=True
        await msg.reply_text("Now attach 📎 → Location and send a map pin for the actual bus stop. Use a regular location pin, not Live Location.")
    else:
        await msg.reply_text("Tap the buttons or send /start to open the menu.",reply_markup=menu())

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg=update.effective_message
    loc=msg.location
    uid=update.effective_user.id
    if not loc: return
    if context.user_data.get("want_pin"):
        name=context.user_data.get("pending_name","Saved stop")
        with connect() as c:
            c.execute("INSERT INTO stops(user_id,name,lat,lon) VALUES(?,?,?,?)",(uid,name,loc.latitude,loc.longitude))
        context.user_data.pop("want_pin",None); context.user_data.pop("pending_name",None)
        await msg.reply_text(f"Stop saved: {name} 📍\nTap Start journey to use it.",reply_markup=menu())
        return
    with connect() as c:
        j=c.execute("""SELECT j.*,s.name,s.lat,s.lon FROM journeys j JOIN stops s ON s.id=j.stop_id
                       WHERE j.user_id=? AND s.user_id=?""",(uid,uid)).fetchone()
        if not j: return
        d=distance_m(loc.latitude,loc.longitude,j["lat"],j["lon"])
        alerts=[]
        if d<=1000 and not j["a1000"]:
            alerts.append(("a1000","👀 OYA, YOUR STOP DEY FRONT SMALL!\nNo go sleep o! Your stop dey about 1 km away."))
        if d<=500 and not j["a500"]:
            alerts.append(("a500","🗣️ OGA, PREPARE YOURSELF!\nYour bus stop dey near. Get your money ready!"))
        if d<=150 and not j["a150"]:
            alerts.append(("a150","😂 OGA DRIVER, OWA O!\nNo pass my bus stop abeg!"))
        if d<=60 and not j["arrived"]:
            alerts.append(("arrived",f"🚌 YOU DON LAND near {j['name']}! Safe journey, my guy."))
        for col,_ in alerts:
            c.execute(f"UPDATE journeys SET {col}=1 WHERE user_id=?",(uid,))
    for _,text in alerts: await msg.reply_text(text)

async def errors(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Bot error",exc_info=context.error)

def main():
    if not TOKEN: raise RuntimeError("Missing BOT_TOKEN environment variable")
    init_db()
    app=Application.builder().token(TOKEN).post_init(setup_menu).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help_cmd))
    app.add_handler(CommandHandler("journey",journey))
    app.add_handler(CommandHandler("addstop",addstop))
    app.add_handler(CommandHandler("stops",stops))
    app.add_handler(CommandHandler("stop",end))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.LOCATION,location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    app.add_error_handler(errors)
    app.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=False)

if __name__=="__main__": main()
