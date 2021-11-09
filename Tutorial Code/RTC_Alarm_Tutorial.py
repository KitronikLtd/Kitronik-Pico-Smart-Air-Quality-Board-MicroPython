from PicoAirQuality import KitronikOLED, KitronikRTC
import time

oled = KitronikOLED()
rtc = KitronikRTC()

rtc.setDate(1, 11, 2021)
rtc.setTime(14, 0, 50)

rtc.setAlarm(14, 1)
while True:
	if rtc.checkAlarm():
		oled.clear()
		oled.displayText("WAKE UP!!!", 3, 20)
		oled.show()
