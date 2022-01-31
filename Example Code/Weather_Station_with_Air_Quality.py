# A weather station program display the date, time, temperature and humidity on the OLED screen with Air Quality and eCO2 on ZIP LEDs (Red/Green)
from PicoAirQuality import KitronikBME688, KitronikOLED, KitronikRTC, KitronikZIPLEDs
import time

bme688 = KitronikBME688()
oled = KitronikOLED()
rtc = KitronikRTC()
zipleds = KitronikZIPLEDs(3)

rtc.setDate(24, 1, 2022)
rtc.setTime(15, 41, 0)

bme688.setupGasSensor()
bme688.calcBaselines()

while True:
    time.sleep_ms(1000)
    bme688.measureData()
    oled.clear()
    oled.drawRect(4, 5, 120, 35)
    oled.displayText(rtc.readDateString(), 2, 25)
    oled.displayText(rtc.readTimeString(), 3, 33)
    oled.drawLine(0, 48, 127, 48)
    oled.drawLine(0, 49, 127, 49)
    oled.displayText(str(bme688.readTemperature()) + " C", 6, 10)
    oled.displayText(str(bme688.readHumidity()) + " %", 6, 80)
    oled.show()
    IAQ = bme688.getAirQualityScore()
    eCO2 = bme688.readeCO2()
    if (IAQ < 100):
        zipleds.setLED(0,  zipleds.GREEN)
    else:
        zipleds.setLED(0, zipleds.RED)
    if (eCO2 < 800):
        zipleds.setLED(2,  zipleds.GREEN)
    else:
        zipleds.setLED(2,  zipleds.RED)
    zipleds.setBrightness(100)
    zipleds.show()
