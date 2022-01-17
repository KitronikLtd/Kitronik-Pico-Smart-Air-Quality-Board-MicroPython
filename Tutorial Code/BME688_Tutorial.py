from PicoAirQuality import KitronikBME688, KitronikOLED
from time import sleep_ms

bme688 = KitronikBME688()
oled = KitronikOLED()

bme688.setupGasSensor()
bme688.calcBaselines()

while True:
	bme688.measureData()
	oled.clear()
    oled.displayText("Temp: " + str(bme688.readTemperature()) + " C", 1)
    oled.displayText("Pres: " + str(bme688.readPressure()) + " Pa", 2)
    oled.displayText("Hum: " + str(bme688.readHumidity()) + " %", 3)
    oled.displayText("IAQ: " + str(bme688.getAirQualityScore()), 4)
    oled.displayText("eCO2: " + str(bme688.readeCO2()) + " ppm", 5)
    oled.show()
	print("Temperature: " + str(bme688.readTemperature()) + " C")
	print("Pressure: " + str(bme688.readPressure()) + " Pa")
	print("Humidity: " + str(bme688.readHumidity()) + " %")
	print("IAQ: " + str(bme688.getAirQualityScore()))
	print("eCO2: " + str(bme688.readeCO2()) + " ppm")
	sleep_ms(2500)