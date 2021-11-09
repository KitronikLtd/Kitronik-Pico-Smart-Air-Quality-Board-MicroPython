from PicoAirQuality import KitronikBME688
from time import sleep_ms

bme688 = KitronikBME688()

bme688.setupGasSensor()
bme688.calcBaselines()

while True:
	bme688.measureData()
	print("Temperature: " + str(bme688.readTemperature()) + " C")
	print("Pressure: " + str(bme688.readPressure()) + " Pa")
	print("Humidity: " + str(bme688.readHumidity()) + " %")
	print("IAQ: " + str(bme688.getAirQualityScore()))
	print("eCO2: " + str(bme688.readeCO2()) + " ppm")
	sleep_ms(2500)