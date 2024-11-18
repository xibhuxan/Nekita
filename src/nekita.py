#!/usr/bin/env python3

""" Este es el bot Nekita.
Para más información, visita https://github.com/xibhuxan/Nekita
También el grupo de la comunidad t.me/NekoMegaBot
"""

__version__ = '0.3'
__author__ = 'Xibhuxan - Carlos'

#t.me/NekoMegaBot
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext
from unidecode import unidecode
import asyncio
import datetime, requests
import random
import hora, scraping, nekomando, persistencia, config

lista_chat_telegram = {}

class ChatTelegram:
    def __init__(self, grupo):
        self.grupo = grupo
        self.usuarios_pole = []
        self.usuarios_puntuacion = {}
        self.orden_pole = 0
        self.participa = True
        self.prueba = True

###################################################
####Saludo
###################################################
async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    nombre = update.effective_user.username
    if nombre is None:
        nombre = update.effective_user.first_name
    else:
        nombre = '@' + nombre
    await update.message.reply_text(f'Hola, {nombre}-nya.')
    


###################################################
####HoraLocal
###################################################
async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    await context.bot.send_message(chat_id=update.message.chat_id, text=f'Son las: {current_time}', reply_to_message_id=update.message.message_id)


###################################################
####DiaLocal
###################################################
async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_day = datetime.datetime.now().strftime("%d-%m-%Y")
    await context.bot.send_message(chat_id=update.message.chat_id, text=f'Hoy es: {current_day}', reply_to_message_id=update.message.message_id)


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
        await update.message.reply_photo(photo=cat_image_url)
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"Todos los nekos están escondidos-nya")


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
        await update.message.reply_photo(photo=dog_image_url)
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"Ahora mismo no veo ningún perrito-nya")


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
        await update.message.reply_photo(photo=cangrejo_image_url)
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"Ahora mismo no veo ningún cangrejito-nya")


###################################################
####Moneda
###################################################
async def moneda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    moneda_image_url = scraping.obtener_enlace_moneda()
    response = requests.get(moneda_image_url)
    if moneda_image_url:
        await update.message.reply_photo(photo=moneda_image_url)
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"Ahora mismo no veo ninguna monedita-nya")


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
    
    await otorgar_pole(update, context)
    
    for comando_respuesta in nekomandos.comandos_respuestas:
        if contenido == comando_respuesta.comando:
            await context.bot.send_message(chat_id=chat_id, text=comando_respuesta.respuesta, reply_to_message_id=update.message.message_id)
            
            return
            
###################################################
####Pole
###################################################
async def otorgar_pole(update, context):
    chat_id = update.message.chat_id
    usuario_nombre = update.message.from_user.username

    chat_telegram = ChatTelegram(chat_id)

    chat_en_lista = any(chat == chat_telegram.grupo for chat in lista_chat_telegram)
    if chat_en_lista:
        chat_telegram = lista_chat_telegram[chat_telegram.grupo]
    else:
        lista_chat_telegram[chat_telegram.grupo] = chat_telegram
    
    if usuario_nombre is None:
        usuario_nombre = update.message.from_user.first_name
    else:
        usuario_nombre = '@' + usuario_nombre

    await comprobar_pole(update, context, chat_telegram, "oro", 0, 3, '¡Enhorabuena ' + usuario_nombre +'! Has ganado la pole-nya')
    await comprobar_pole(update, context, chat_telegram, "plata", 1, 2, '¡Enhorabuena ' + usuario_nombre +'! Has ganado la plata-nya')
    await comprobar_pole(update, context, chat_telegram, "bronce", 2, 1, '¡Enhorabuena ' + usuario_nombre +'! Has ganado el bronce-nya')


async def comprobar_pole(update, context, chat_telegram, texto, puesto, puntos, mensaje_salida):
    chat_id = update.message.chat_id
    usuario_id = update.message.from_user.id
    usuario_nombre = update.message.from_user.username
    texto_mensaje = update.message.text.lower()
    grupo_concreto = lista_chat_telegram[chat_telegram.grupo]

    if usuario_nombre is None:
        usuario_nombre = update.message.from_user.first_name


    if texto_mensaje == texto and usuario_id not in grupo_concreto.usuarios_pole and grupo_concreto.orden_pole == puesto:
        await context.bot.send_message(chat_id=chat_id, text=f'{mensaje_salida}')
        grupo_concreto.usuarios_pole.append(usuario_id)

        if usuario_nombre not in grupo_concreto.usuarios_puntuacion:
            grupo_concreto.usuarios_puntuacion[usuario_nombre] = 0

        grupo_concreto.usuarios_puntuacion[usuario_nombre] += puntos
        grupo_concreto.orden_pole = puesto + 1

async def mostrar_puntos(update, context):
    texto = 'Puntuaciones de pole-nya!'
    diccionario_ordenado_ascendente = dict(sorted(lista_chat_telegram[update.message.chat_id].usuarios_puntuacion.items(), key=lambda item: item[1], reverse=True))

    for clave, valor in diccionario_ordenado_ascendente.items():
        texto += f'\n{clave}~{valor}'
    await context.bot.send_message(chat_id=update.message.chat_id, text=texto)


###################################################
####Help
###################################################
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text=f'Mis comandos son los siguientes-nya'+
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
    '\nPole palitos'+
    '\nPole patitos'+
    '\nPole cuack'+
    '\nDobby'+
    '\nPLC'+
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


###################################################
####Saludo y despedida
###################################################
async def in_out_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message
    if member.new_chat_members:
        await update.message.reply_text(f'Hola {member.from_user.first_name}, saluda a tus tomodachis-nya!! (^_^)')
    if member.left_chat_member:
        await update.message.reply_text(f'Nuestro amigo {member.from_user.first_name} abandona el grupo.')

###################################################
####Temporizadores
###################################################

#async def arranque(context: ContextTypes.DEFAULT_TYPE):
#    await context.bot.send_message(chat_id = config.USUARIO_MASTER, text=f"Arranqué")

async def guardar_puntuaciones_programada(context: ContextTypes.DEFAULT_TYPE):
    persistencia.guardar_datos(lista_chat_telegram, "grupos_pole.pkl")

async def guardar_puntuaciones_programada1(update: Update,context: ContextTypes.DEFAULT_TYPE):
    persistencia.guardar_datos(lista_chat_telegram, "grupos_pole.pkl")

async def cargar_puntuaciones_programada( context: ContextTypes.DEFAULT_TYPE):
    global lista_chat_telegram
    lista_chat_telegram = persistencia.cargar_datos("grupos_pole.pkl")


async def limpiar_pole_diaria(context: ContextTypes.DEFAULT_TYPE):
    for clave, grupo in lista_chat_telegram.items():
        grupo.usuarios_pole = []
        grupo.orden_pole = 0

###################################################
####Main
###################################################
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.TOKEN).build()

    temporizador = app.job_queue

#    temporizador.run_once(arranque, 1)
    temporizador.run_once(cargar_puntuaciones_programada, 1)

    hora_limpieza = datetime.time(hour=22, minute=59, second=59)
    temporizador.run_daily(limpiar_pole_diaria, hora_limpieza)

    hora_guardado = datetime.time(hour=20, minute=00, second=00)
    temporizador.run_daily(guardar_puntuaciones_programada, hora_guardado)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hola", hola))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("dia", get_day))
    app.add_handler(CommandHandler("hora", get_time))
    app.add_handler(CommandHandler("neko", gato))
    app.add_handler(CommandHandler("perro", perro))
    app.add_handler(CommandHandler("cangrejo", cangrejo))
    app.add_handler(CommandHandler("moneda", moneda))
    app.add_handler(CommandHandler("backup", guardar_puntuaciones_programada))
    app.add_handler(CommandHandler("id", obtener_id_grupo))
    app.add_handler(CommandHandler("pole", mostrar_puntos))
    app.add_handler(CommandHandler("guardar", guardar_puntuaciones_programada1))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, in_out_member))
    app.add_handler(MessageHandler(filters.TEXT, manejar_mensajes))
    

    app.run_polling()





