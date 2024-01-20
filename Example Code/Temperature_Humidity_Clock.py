# A simple weather station program display the date, time, temperature and humidity on the OLED screen
from PicoAirQuality import KitronikBME688, KitronikOLED, KitronikRTC
import time

bme688 = KitronikBME688()
oled = KitronikOLED()
rtc = KitronikRTC()

rtc.setDate(1, 11, 2021)
rtc.setTime(14, 0, 0)

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
