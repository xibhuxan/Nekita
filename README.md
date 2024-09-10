
# Nekita
¡Soy el bot con el que no te aburrirás con tus compañeros de grupo en Telegram! Yo, @NekoMegaBot, alias Nekita, soy capaz de entreteneros y haceros pasar un buen rato-nya. Puedo hacer que compitáis por la pole, enseñaros gatitos, o tomar decisiones por ustedes. ¡Que sois muy vagos-nya!

No dejes de lado a Nekita, yo nunca te dejaría-nya.

# Uso
Cualquier persona puede usar a Nekita añadiendo a [@NekoMegaBot](https://t.me/NekoMegaBot) a su grupo de telegram o directamente interactuando con ella en un chat privado.

Existe un grupo de asistencia, soporte y sugerencias de funcionalidades, este es [@NekoMegaBotSoporte](https://t.me/NekoMegaBotSoporte).

Si se quiere crear a su propia Nekita, se debe crear un bot de telegram con BotFather. Una vez hecho, seguir los pasos de instalación.

# Instalación

Estas instrucciones están hechas específicamente para Debian (Linux). Hacer el símil para cada sistema operativo si es necesario.

Clonar el repositorio.

    git clone https://github.com/xibhuxan/Nekita.git

Instalar python.

    sudo apt install python3
    o
    sudo apt install python3-full

Instalar los entornos virtuales

    sudo apt install python3-venv

Dentro de la carpeta de src crear una carpeta para entonrno vitual.

Crear un entorno nuevo dentro de esa carpeta con

    python3 -m venv miCarpeta

Usar ese entorno cada vez que se quiera trabajar.

    source miCarpeta/bin/activate

(Secundario) Para dejar de usar ese entorno.

    deactivate

Instalar las librerías con pip, una vez dentro del entorno.

    pip install -r requirements.txt

Y todos los que te vaya pidiendo que no tengas.

    pip install paquete
    o
    pip install paquete[subpaquete]

En el archivo config.py colocar tu TOKEN de bot recibido de BotFather.

Ejecutar a nekita.

    ./nekita.py
    o
    python3 ./nekita.py

# Objetivos conseguidos

- [x] Nekos (gatos)
- [x] Perros
- [x] Cangrejos
- [x] Saludos
- [x] Horas
- [X] Pole


# Objetivos por conseguir

- [ ] Pole personalizada
- [ ] Mensajes pole
- [ ] Paulo
- [ ] Dragonite

# Changelog

v0.3  
Modificado README.md - Añadido explicación puesta en marcha.  
Añadido saludo y despedida al entrar y salir del grupo.  

v0.2  
Realizado Pole.  
Persistencia de los puntos con guardado diario y manual.  
Carga de los puntos al arrancar el programa.  

v0.1  
Primer commit!  






