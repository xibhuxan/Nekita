import requests
from bs4 import BeautifulSoup
import re, random

def obtener_enlace_moneda():
    try:
           
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


        cookies = {"cookie_name": "cookie_value"}
        url = "https://www.dreamstime.com/photos-images/coins.html"

        # Realizar la solicitud GET a la URL
        respuesta = requests.get(url, headers=headers, cookies=cookies)
        respuesta.raise_for_status()  # Verificar si hay errores en la solicitud
        
        # Crear un objeto BeautifulSoup para analizar el HTML
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Encontrar todos los elementos <a> (enlaces)
        enlaces = []
        for link in soup.find_all('a'):
            enlaces.append(link.get('href'))

        # Filtrar enlaces que terminan en "image" seguido de números
        patron = re.compile(r'^https://www\.dreamstime\.com/.*image\d+$')
        enlaces_filtrados = [enlace for enlace in enlaces if isinstance(enlace, str) and patron.match(enlace)]
        
        enlace_aleatorio = random.choice(enlaces_filtrados)
        
        return transformar_enlace(enlace_aleatorio)
        

        

    except requests.exceptions.RequestException as e:
        print("Error en la solicitud:", e)


def transformar_enlace(enlace):
    # Obtener el ID de la imagen desde el enlace original
    id_imagen = enlace.split("-")[-1]

    # Obtener la parte después de la última barra "/"
    parte_final = enlace.rsplit("/", 1)[-1]

    # Eliminar la palabra "image" y el guion del enlace original
    parte_final_sin_image = parte_final.replace("image", "")

    # Construir el nuevo enlace
    nuevo_enlace = f"https://thumbs.dreamstime.com/z/{parte_final_sin_image}.jpg"

    return nuevo_enlace
