import hora

class ComandoRespuesta:
    def __init__(self, comando, respuesta):
        self.comando = comando
        self.respuesta = respuesta

class Nekomandos:
    def __init__(self, mensaje):
        self.chat_id = mensaje.chat_id
        self.usuario = mensaje.from_user
        self.contenido = mensaje.text
        self.nombre = self.usuario.username
        
        if self.nombre is None:
            self.nombre = self.usuario.first_name
        else:
            self.nombre = '@' + self.nombre


        self.comandos_respuestas = [
        ComandoRespuesta("hola china", hora.hora_zona_horaria("Asia/Shanghai")),
        ComandoRespuesta("hora", hora.hora_zona_horaria("Europe/Madrid")),
        ComandoRespuesta("hora canaria", hora.hora_zona_horaria("Atlantic/Canary")),
        ComandoRespuesta("hora rusa", hora.hora_zona_horaria("Europe/Moscow")),
        ComandoRespuesta("hora venezuela", "Sin comida no hay hora."),
        ComandoRespuesta("pole canaria", "A las 12:00 de canarias"),
        ComandoRespuesta("pole peninsular", "A las 11:00 de canarias"),
        ComandoRespuesta("pole andaluza", "Hazla cuando quieras, pero a las 06:00 península está bien-nya."),
        ComandoRespuesta("pole palitos", "A las 11:11, tú puedes-nya!"),
        ComandoRespuesta("pole patitos", "A las 22:22, tú puedes-nya!"),
        ComandoRespuesta("pole cuack", "A las 22:22, tú puedes-nya!"),
        ComandoRespuesta("pole patitos canarias", "A las 22:22, tú puedes-nya!"),
        ComandoRespuesta("pole cuack canarias", "A las 22:22, tú puedes-nya!"),
        ComandoRespuesta("dobby", f"Dobby no tiene amo Dobby es un elfo libre"),
        ComandoRespuesta(":)", ":)"),
        ComandoRespuesta(":(", "Sonríe, eres especial-nya!!"),
        ComandoRespuesta(":3", "¯\_(=^･ω･^)_/¯"),
        ComandoRespuesta("buenos dias", f"Buenos días @{self.nombre} para ti también."),
        ComandoRespuesta("buenas tardes", f"Buenas tardes {self.nombre}, ¿ya has comido-nya?"),
        ComandoRespuesta("buenas noches", f"Buenas noches {self.nombre}, que duermas bien-NYA!!"),
        ComandoRespuesta("buenas", f"Hola, {self.nombre}, ¿qué tal?"),
        ComandoRespuesta("hola", f"Hola, {self.nombre}, ¿qué tal?"),
        ComandoRespuesta("plc", f"Eso te lo hago yo con un Arduino de 3 euros."),
    ]
