import datetime
import schedule
import time
import persistencia


puntuaciones = {}

def otorgar_puntos(usuario, puntos):
    if usuario in puntuaciones:
        puntuaciones[usuario] += puntos
    else:
        puntuaciones[usuario] = puntos


async def handle_message(update, context):
    message_text = update.message.text.lower()
    user_id = update.effective_user.id

    if message_text == "oro" and user_id not in puntuacion:
        await context.bot.send_message(chat_id=chat_id, text="estoy aqui oro")
    elif message_text == "plata" and user_id not in puntuacion:
        otorgar_puntos(user_id, 2)
    elif message_text == "bronce" and user_id not in puntuacion:
        otorgar_puntos(user_id, 1)
    
    
