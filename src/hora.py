import schedule
import time
import pytz
import subprocess
from multiprocessing import Process
from datetime import datetime

def sync_time_with_ntp(server="pool.ntp.org"):
    try:
        subprocess.run(["sudo", "ntpdate", server])
        print(f"Hora actual sincronizada desde {server}")
    except Exception as e:
        print(f"Error al sincronizar la hora: {e}")

def schedule_sync():
    # Programa la tarea para que se ejecute una vez al día a una hora específica
    schedule.every().day.at("09:00").do(sync_time_with_ntp)

    while True:
        schedule.run_pending()
        time.sleep(1)


def sync_hour():
    sync_process = Process(target=schedule_sync)
    sync_process.start()


def hora_zona_horaria(zona_horaria_deseada):

    # Obtén el objeto de zona horaria
    zona_horaria = pytz.timezone(zona_horaria_deseada)

    # Obtiene la hora actual en la zona horaria deseada
    hora_actual = datetime.now(zona_horaria)

    # Imprime la hora actual
    texto_hora = f"En {zona_horaria_deseada} son las: {hora_actual.strftime('%H:%M:%S')}"
    return texto_hora


