from time import sleep

from database import registry
from engines.ais import AISStreamEngine


engine = AISStreamEngine()

engine.start()

print("AIS Engine fut...")

while True:

    sleep(5)

    print(f"Hajók: {registry.count()}")
