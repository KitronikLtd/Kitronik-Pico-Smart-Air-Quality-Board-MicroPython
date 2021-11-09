from PicoAirQuality import KitronikOLED, KitronikOutputControl
import time

oled = KitronikOLED()
output = KitronikOutputControl()

analogIn = machine.ADC(26) # ADC0 on the Pico Smart Air Quality Board
output.registerServo()
while True:
	# Analog Input
	oled.clear()
	oled.displayText("Analog In", 2)
	oled.displayText(str(analogIn.read_u16()), 3)
	oled.show()
	time.sleep_ms(2500)
	# Servo
	oled.clear()
	oled.displayText("Servo", 2)
	oled.show()
	output.servoToPosition(0)
	time.sleep_ms(1000)
	output.servoToPosition(180)
	time.sleep_ms(1000)
	# High-Power Outputs
	oled.clear()
	oled.displayText("High-Power Out", 2)
	oled.show()
	output.highPowerOn(15)
	output.highPowerOn(3)
	time.sleep_ms(1000)
	output.highPowerOff(15)
	output.highPowerOff(3)
	time.sleep_ms(1000)
