import sys
# adding microdot path for simpler import
sys.path.insert(1, 'microdot/')
import asyncio
from microdot import Microdot
from controller import MicroBrewery
import time
import sys

debugmode = False

app = Microdot()
controller = MicroBrewery("microbrew", debugmode )

@app.route('/')
async def index(request):
    return 'Hello, Brewery! 🍺'

@app.get('/metrics')
async def index(request):
    return controller.getMetrics()

@app.get('/prometheus')
async def index(request):
    return controller.json_to_prometheus(controller.getMetrics())

@app.post('/control')
async def control(request):
    # logic to set parameters go here
    for item, value in request.json.items():
        print(f"key:{item}, value:{value}")
        controller.setControlValue(item,value)
    return controller.getControlProfile()

async def sensorLoop():
    print("entering sensorloop")
    while True:
        if controller.getControlProfile()['temperatureSensor'] == 'raptpill':
              print(f"temp: {controller.getTemperature()}")
              await asyncio.sleep(1)
        else:
              print("pill not set")
              await asyncio.sleep(1)

async def thermalLoop():
    print("entering thermalLoop")
    while True:
        print(f"State: {controller.update_temperature()}")
        await asyncio.sleep(5)

async def main():
    sensor  = asyncio.create_task(sensorLoop())
    thermal = asyncio.create_task(thermalLoop())
    server  = asyncio.create_task(app.run(port=80))

    # cleanup
    await asyncio.sleep(10)

asyncio.run(main())
