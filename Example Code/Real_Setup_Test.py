# Example code for a control and data logging program (designed to work in the Kitronik Smart Greenhouse):
# A water pump was attached to GP15 high-power output
# A mini 180 degree servo was attached to the servo output
# A ZIP Stick was attached to the ZIP LED extension connection
# A Mini Prong moisture sensor was attached to the ADC0 input
from PicoAirQuality import KitronikBME688, KitronikOLED, KitronikRTC, KitronikZIPLEDs, KitronikBuzzer, KitronikDataLogger, KitronikOutputControl, KitronikButton
import time

logFileName = "data_log.txt"

bme688 = KitronikBME688()
oled = KitronikOLED()
rtc = KitronikRTC()
zipleds = KitronikZIPLEDs(8)    # Initialise the ZIP LEDs with 8 as there are 3 onboard and 5 on the external ZIP Stick
buzzer = KitronikBuzzer()
log = KitronikDataLogger(logFileName, "semicolon")
output = KitronikOutputControl()
buttons = KitronikButton()

rtc.setDate(15, 11, 2021)
rtc.setTime(15, 30, 0)

# Button A will display the current date and time and some key measurement data on the OLED screen and turn on some onbaord ZIP LEDs
def ButtonA_IRQHandler(pin):
    oled.clear()
    oled.displayText(rtc.readDateString(), 1)
    oled.displayText(rtc.readTimeString(), 2)
    oled.displayText("T: " + str(bme688.readTemperature()), 4)
    oled.displayText("IAQ: " + str(bme688.getAirQualityScore()), 5)
    oled.displayText("eCO2: " + str(bme688.readeCO2()), 6)
    oled.show()
    zipleds.setLED(0, zipleds.RED)
    zipleds.setLED(2, zipleds.GREEN)
    zipleds.setBrightness(50)
    zipleds.show()

# Button B will clear the OLED screen and the ZIP LEDs
def ButtonB_IRQHandler(pin):
    oled.clear()
    oled.show()
    for led in range(8):
        zipleds.clear(led)
    zipleds.show()
    
buttons.buttonA.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonA_IRQHandler)
buttons.buttonB.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonB_IRQHandler)

bme688.setupGasSensor()
bme688.calcBaselines()

prong = machine.ADC(26)     # Sets up the Mini Prong input with ADC0, which is associated with GP26
output.registerServo()      # Setup the servo ready for use
log.writeProjectInfo("User Name", "Project Name")
log.setupDataFields("Date", "Time", "Temperature", "Pressure", "Humidity", "Soil Moisture", "IAQ", "eCO2")
rtc.setAlarm(16, 0)     # Set an initial alarm for when the first control actions occur and data is logged

while True:
    # These actions only occur when the alarm time conditions are met
    if rtc.checkAlarm():
        # Measure and log data
        bme688.measureData()
        log.storeDataEntry(rtc.readDateString(), rtc.readTimeString(), str(bme688.readTemperature()), str(bme688.readPressure()), str(bme688.readHumidity()), str(prong.read_u16()), str(bme688.getAirQualityScore()), str(bme688.readeCO2()))
        # Move the servo to position 45 degrees and turn high-power output on GP15 ON
        output.servoToPosition(45)
        output.highPowerOn(15)
        time.sleep_ms(1000)
        # After 1s pause, move the servo to position 135 degrees and turn OFF the high-power output
        output.servoToPosition(135)
        output.highPowerOff(15)
        # Silence the alarm so it does not keep triggering
        rtc.silenceAlarm()
        # Set a new alarm for 30 mins in the future, taking account of the 'new day' cross-over point
        if (rtc.readParameter("min") == 0):
            alarmMin = 30
        else:
            alarmMin = 0
            alarmHour = rtc.readParameter("h") + 1
            if (alarmHour == 24):
                alarmHour = 0
        rtc.setAlarm(alarmHour, alarmMin)
        # Turn the ZIP Stick on all yellow for 10s
        zipleds.setLED(3, zipleds.YELLOW)
        zipleds.setLED(4, zipleds.YELLOW)
        zipleds.setLED(5, zipleds.YELLOW)
        zipleds.setLED(6, zipleds.YELLOW)
        zipleds.setLED(7, zipleds.YELLOW)
        zipleds.setBrightness(75)
        zipleds.show()
        time.sleep_ms(10000)
        # Turn off the ZIP LEDs
        for led in range(8):
            zipleds.clear(led)
        zipleds.show()


