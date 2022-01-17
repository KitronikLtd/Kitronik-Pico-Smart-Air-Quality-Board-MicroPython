from PicoAirQuality import KitronikOLED, KitronikOutputControl
import time

oled = KitronikOLED()
output = KitronikOutputControl()

oled.clear()
# Servo
oled.displayText("Servo", 2)
# High-Power Outputs
oled.displayText("High-Power Out", 2)
oled.show()

analogIn = machine.ADC(26) # ADC0 on the Pico Smart Air Quality Board

while True:
	# Analog Input
	oled.clear()
	oled.displayText("Analog In: " + str(analogIn.read_u16()), 1)
	oled.plot(analogIn.read_u16())
	oled.show()
	time.sleep_ms(100)
	# Servo
	oled.clearLine(3)
	oled.displayText("Servo to 0", 3)
	oled.show()
	output.servoToPosition(0)
	time.sleep_ms(1000)
	oled.clearLine(3)
	oled.displayText("Servo to 180", 3)
	oled.show()
	output.servoToPosition(180)
	time.sleep_ms(1000)
	# High-Power Outputs
	oled.clearLine(3)
	oled.displayText("Outputs On", 3)
	oled.show()
	output.highPowerOn(15)
	output.highPowerOn(3)
	time.sleep_ms(1000)
	oled.clearLine(3)
	oled.displayText("Outputs Off", 3)
	oled.show()
	output.highPowerOff(15)
	output.highPowerOff(3)
	time.sleep_ms(1000)
