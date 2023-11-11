#t.me/NekoMegaBot


from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext
from unidecode import unidecode
import datetime, requests
import random
import hora, pole, scraping, nekomando, persistencia, config

token = config.token

###################################################
####Saludo
###################################################
async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hola {update.effective_user.first_name}-nya.')


###################################################
####HoraLocal
###################################################
async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    await update.message.send_message(f'Son las: {current_time}')


###################################################
####DiaLocal
###################################################
async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_day = datetime.datetime.now().strftime("%d-%m-%Y")
    await update.message.send_message(f'Hoy es: {current_day}')


###################################################
####Gatito
###################################################
def get_random_cat_image():
    url = "https://api.thecatapi.com/v1/images/search"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data and "url" in data[0]:
            return data[0]["url"]
    return None
async def gato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cat_image_url = get_random_cat_image()
    if cat_image_url:
        await update.message.send_message(photo=cat_image_url)
    else:
        await update.message.send_message("Todos los nekos están escondidos-nya")


###################################################
####Perrito
###################################################
def get_random_dog_image():
    url = "https://random.dog/woof.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data and "url" in data:
            return data["url"]
    return None
async def perro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    dog_image_url = get_random_dog_image()
    if dog_image_url:
        await update.message.send_message(photo=dog_image_url)
    else:
        await update.message.send_message("Ahora mismo no veo ningún perrito-nya")


###################################################
####Cangrejo
###################################################
async def cangrejo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cangrejo_image_url1 = "https://generatorfun.com/code/uploads/Random-Crab-image-"
    cangrejo_image_url2 = ".jpg"
    numero = str(random.randint(1,19))
    cangrejo_image_url = cangrejo_image_url1 + numero + cangrejo_image_url2
    response = requests.get(cangrejo_image_url)
    if cangrejo_image_url:
        await update.message.send_message(photo=cangrejo_image_url)
    else:
        await update.message.send_message("Ahora mismo no veo ningún cangrejito-nya")


###################################################
####Moneda
###################################################
async def moneda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    moneda_image_url = scraping.obtener_enlace_moneda()
    response = requests.get(moneda_image_url)
    if moneda_image_url:
        await update.message.send_message(photo=moneda_image_url)
    else:
        await update.message.send_message("Ahora mismo no veo ningún cangrejito-nya")


###################################################
####IDGrupo
###################################################
async def obtener_id_grupo(update, context):
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text=f"El ID de este grupo es: {chat_id}")


###################################################
####LeerGrupo
###################################################
async def manejar_mensajes(update, context):
    mensaje = update.message
    chat_id = mensaje.chat_id
    usuario_id = mensaje.from_user.id
    contenido = unidecode(mensaje.text.lower())
    nekomandos = nekomando.Nekomandos(mensaje)

    await manejar_pole(update, context)
    
    for comando_respuesta in nekomandos.comandos_respuestas:
        if contenido == comando_respuesta.comando:
            await context.bot.send_message(chat_id=chat_id, text=comando_respuesta.respuesta)
            return


###################################################
####LeerPole
###################################################
async def manejar_pole(update, context):
    mensaje = update.message
    chat_id = mensaje.chat_id
    usuario_id = mensaje.from_user.id
    contenido = unidecode(mensaje.text.lower())
    
    
    if contenido == "oro":
        pole.handle_message(update, context)
            

###################################################
####Help
###################################################
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Mis comandos son los siguientes-nya'
    '\n/start'+    
    '\n/hola'+
    '\n/help'+
    '\n/neko'+
    '\n/perro'+
    '\n/cangrejo'+
    '\n/dia'+
    '\n/id'+
    '\n¡Y muchos otros comandos más directamente escritos! Como por ejemplo:'+
    '\nHola china'+
    '\nHora'+
    '\nHora canaria'+
    '\nHora rusa'+
    '\nHora venezuela'+
    '\nPole canaria'+
    '\nPole peninsular'+
    '\nPole andaluza'+
    '\nPole patitos'+
    '\nPole cuack'+
    '\nDobby'+
    '\n:)'+
    '\n:('+
    '\n:3'+
    '\nBuenos días'+
    '\nBuenas tardes'+
    '\nBuenas noches'+
    '\nBuenas'+
    '\nHola')


###################################################
####Start
###################################################
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Puedo hacer muchas cosas por tu grupo. Soy una sustituta definitiva para que podáis hacer poles, enviar nekos a tu amigo favorito y mucho más. Pregúntame qué puedo hacer con /help')


async def guardar_puntuaciones_programada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    t = datetime.time(hour=10, minute=00, second=00)
    context.job_queue.run_daily(persistencia.guardar_datos(pole.puntuaciones, "score.pkl"), t)
    context.job_queue.run_once(alarm, due, chat_id=chat_id, name=str(chat_id), data=due)
###################################################
####Main
###################################################
if __name__ == "__main__":
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hola", hola))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("dia", get_day))
    app.add_handler(CommandHandler("neko", gato))
    app.add_handler(CommandHandler("perro", perro))
    app.add_handler(CommandHandler("cangrejo", cangrejo))
    app.add_handler(CommandHandler("moneda", moneda))
    #app.add_handler(CommandHandler("backup", guardar_puntuaciones_programada))
    app.add_handler(CommandHandler("id", obtener_id_grupo))
    app.add_handler(MessageHandler(filters.TEXT, manejar_mensajes))

    persistencia.cargar_datos(pole.puntuaciones, "score.pkl")


    
    app.run_polling()

