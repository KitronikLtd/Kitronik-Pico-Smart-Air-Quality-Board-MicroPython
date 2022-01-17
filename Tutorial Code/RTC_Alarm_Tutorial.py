from PicoAirQuality import KitronikOLED, KitronikRTC
import time

oled = KitronikOLED()
rtc = KitronikRTC()

rtc.setDate(1, 11, 2021)
rtc.setTime(14, 0, 50)

rtc.setAlarm(14, 1)

while True:
	if rtc.checkAlarm():
		oled.clearLine(3)
		oled.displayText("WAKE UP!!!", 3, 20)
		oled.show()
		time.sleep(5)
		rtc.silenceAlarm()
		oled.clearLine(3)
		oled.show()

# Periodic Alarm
#rtc.setAlarm(14, 2, True, 0, 2)

#while True:
#    if rtc.checkAlarm():
#        oled.clearLine(3)
#        oled.displayText("2 MINS", 3, 25)
#        oled.show()
#        time.sleep(5)
#        rtc.silenceAlarm()
#        oled.clearLine(3)
#        oled.show()
