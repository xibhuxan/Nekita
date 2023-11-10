import pickle

def cargar_datos(datos, nombre):
    try:
        with open(nombre, 'rb') as archivo:
            datos = pickle.load(archivo)
            return datos
    except FileNotFoundError:
        return {}

def guardar_datos(datos, nombre):
    # Guarda el diccionario en un archivo usando pickle
    with open(nombre, 'wb') as archivo:
        pickle.dump(datos, archivo)

