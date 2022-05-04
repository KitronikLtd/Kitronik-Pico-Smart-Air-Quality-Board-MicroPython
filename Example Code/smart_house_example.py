# Example code for a smart home monitoring, control and data logging program using the Pico Smart Air Quality board
# A heater pad is attached to GP15 high-power output
# A mini 180 degree servo is attached to the servo output
# A ZIP Stick is attached to the ZIP LED extension connection

# Import the required modules and classes
from PicoAirQuality import KitronikBME688, KitronikOLED, KitronikRTC, KitronikZIPLEDs, KitronikBuzzer, KitronikDataLogger, KitronikOutputControl, KitronikButton
from machine import Timer
import time

logFileName = "house_data.txt"  # Set a name for the data log file
# Create instances of all the classes required from the PicoAirQuality library
bme688 = KitronikBME688()
oled = KitronikOLED()
rtc = KitronikRTC()
zipleds = KitronikZIPLEDs(8)    # Initialise the ZIP LEDs with 8 as there are 3 onboard and 5 on the external ZIP Stick
buzzer = KitronikBuzzer()
log = KitronikDataLogger(logFileName, "semicolon")  # Delimit the log file with semicolons
output = KitronikOutputControl()
buttons = KitronikButton()
# Set the initial date and time
rtc.setDate(31, 3, 2022)
rtc.setTime(10, 30, 0)

# Comparison constants for device control
TEMPERATURE_THRESHOLD_LOW = 10
TEMPERATURE_THRESHOLD_HIGH = 25
HUMIDITY_THRESHOLD = 60
IAQ_THRESHOLD_MED = 50
IAQ_THRESHOLD_HIGH = 100
CO2_THRESHOLD_MED = 700
CO2_THRESHOLD_HIGH = 1000
LIGHT_ON_TIME = 18
LIGHT_OFF_TIME = 7

# Climate data variables, current and previous
prevTemp = 0
temp = 0
prevPress = 0
press = 0
prevHumid = 0
humid = 0
prevIAQ = 0
IAQ = 0
prevCO2 = 0
CO2 = 0
# Climate value comparison variables
humidHigh = False
tempHigh = False
tempLow = False
# Device status variables
windowOpen = False
heaterOn = False
lightOn = False
windowStatus = "CLOSED"
heaterStatus = "OFF"
lightStatus = "OFF"
lightTimingControl = False
# Display Screen Variables
currentScreen = 0 # 0 = Main Menu, 1 = Data Display, 2 = Device Status, 3 = Light Control
menuMarker = "  *"
menuOption = 1
# ZIP LED Colour Options
lightSetting = 4 # 0 = White, 1 = Red, 2 = Green, 3 = Blue, 4 = Off
colours = [zipleds.WHITE, zipleds.RED, zipleds.GREEN, zipleds.BLUE]

# Show the Main Menu - the initial screen which gives access to the data and control screens
def showMainMenu():
    global menuOption
    global currentScreen
    currentScreen = 0
    menuOption = 1
    oled.clear()
    oled.displayText("MAIN MENU", 1, 30)
    oled.displayText("DATA DISPLAY" + menuMarker, 3)
    oled.displayText("DEVICE STATUS", 4)
    oled.displayText("LIGHT CONTROL", 5)
    oled.show()

# Show the data display screen - displays the current temperature, pressure, humidity, air quality index and estimated CO2
def showDataDisplay():
    global currentScreen
    currentScreen = 1
    bme688.measureData()
    oled.clear()
    oled.displayText("CLIMATE DATA", 1, 20)
    oled.displayText("T: " + str(bme688.readTemperature()) + " C", 2)
    oled.displayText("P: " + str(bme688.readPressure()) + " Pa", 3)
    oled.displayText("H: " + str(bme688.readHumidity()) + " %", 4)
    oled.displayText("IAQ: " + str(bme688.getAirQualityScore()), 5)
    oled.displayText("eCO2: " + str(bme688.readeCO2()) + " ppm", 6)
    oled.show()

# Show the device status screen - displays the curent status of the window (OPEN/CLOSED), heater and lights (ON/OFF)
def showDeviceStatus():
    global currentScreen
    global windowOpen
    global heaterOn
    global lightOn
    global windowStatus
    global heaterStatus
    global lightStatus
    currentScreen = 2
    if windowOpen:
        windowStatus = "OPEN"
    else:
        windowStatus = "CLOSED"

    if heaterOn:
        heaterStatus = "ON"
    else:
        heaterStatus = "OFF"

    if lightOn:
        lightStatus = "ON"
    else:
        lightStatus = "OFF"

    oled.clear()
    oled.displayText("DEVICE STATUS", 1, 15)
    oled.displayText("WINDOW: " + windowStatus, 3)
    oled.displayText("HEATER: " + heaterStatus, 4)
    oled.displayText("LIGHTS: " + lightStatus, 5)
    oled.show()

# Show the light control menu - enables control of the lights being on/off and what colour they will be
def showLightControl():
    global menuOption
    global currentScreen
    currentScreen = 3
    menuOption = 1
    oled.clear()
    oled.displayText("LIGHT CONTROL", 1, 15)
    oled.displayText("WHITE" + menuMarker, 2)
    oled.displayText("RED", 3)
    oled.displayText("GREEN", 4)
    oled.displayText("BLUE", 5)
    oled.displayText("OFF", 6)
    oled.show()

# Button A makes selections on menus
def checkButtonA(callBackParam):
    global buttonAState
    global currentScreen
    global menuOption
    global lightSetting
    buttonAState = buttonAState <<1 | buttons.buttonA.value() |0xE000
    buttonAState &=0xFFFF
    if buttonAState == 0xEFFF: #button A has been pressed and passes the debouncing test
        # Main Menu
        if (currentScreen == 0):
            if (menuOption == 1):
                showDataDisplay()
            elif (menuOption == 2):
                showDeviceStatus()
            elif (menuOption == 3):
                showLightControl()
        # Light Control
        elif (currentScreen == 3):
            lightSetting = (menuOption - 1)
            showMainMenu()

# Button B scrolls through menu options and/or returns to the main menu
def checkButtonB(callBackParam):
    global buttonBState
    global currentScreen
    global menuOption
    buttonBState = buttonBState <<1 | buttons.buttonB.value() |0xE000
    buttonBState &=0xFFFF
    if buttonBState == 0xEFFF: #button B has been pressed and passes the debouncing test
        # Main Menu
        if (currentScreen == 0):
            if (menuOption == 1):
                menuOption = 2
                oled.clearLine(3)
                oled.displayText("DATA DISPLAY", 3)
                oled.clearLine(4)
                oled.displayText("DEVICE STATUS" + menuMarker, 4)
                oled.show()
            elif (menuOption == 2):
                menuOption = 3
                oled.clearLine(4)
                oled.displayText("DEVICE STATUS", 4)
                oled.clearLine(5)
                oled.displayText("LIGHT CONTROL" + menuMarker, 5)
                oled.show()
            elif (menuOption == 3):
                menuOption = 1
                oled.clearLine(5)
                oled.displayText("LIGHT CONTROL", 5)
                oled.clearLine(3)
                oled.displayText("DATA DISPLAY" + menuMarker, 3)
                oled.show()
        # Data Display
        elif (currentScreen == 1):
            showMainMenu()
        # Device Status
        elif (currentScreen == 2):
            showMainMenu()
        # Light Control
        elif (currentScreen == 3):
            if (menuOption == 1):
                menuOption = 2
                oled.clearLine(2)
                oled.displayText("WHITE", 2)
                oled.clearLine(3)
                oled.displayText("RED" + menuMarker, 3)
                oled.show()
            elif (menuOption == 2):
                menuOption = 3
                oled.clearLine(3)
                oled.displayText("RED", 3)
                oled.clearLine(4)
                oled.displayText("GREEN" + menuMarker, 4)
                oled.show()
            elif (menuOption == 3):
                menuOption = 4
                oled.clearLine(4)
                oled.displayText("GREEN", 4)
                oled.clearLine(5)
                oled.displayText("BLUE" + menuMarker, 5)
                oled.show()
            elif (menuOption == 4):
                menuOption = 5
                oled.clearLine(5)
                oled.displayText("BLUE", 5)
                oled.clearLine(6)
                oled.displayText("OFF" + menuMarker, 6)
                oled.show()
            elif (menuOption == 5):
                menuOption = 1
                oled.clearLine(6)
                oled.displayText("OFF", 6)
                oled.clearLine(2)
                oled.displayText("WHITE" + menuMarker, 2)
                oled.show()

# Change the ZIP Stick LEDs based on what the user has set in the Light Control Menu              
def controlLights(setting):
    global lightOn
    if (setting == 4):
        lightOn = False
        for led in range(3, 8):
            zipleds.clear(led)
        zipleds.show()
    else:
        lightOn = True
        for led in range(3, 8):
            zipleds.setLED(led, colours[setting])
        zipleds.setBrightness(75)
        zipleds.show()

# Open or close the window based on the action setting
def controlWindow(action):
    global windowOpen
    if (action == "open"):
        windowOpen = True
        output.servoToPosition(90)
    else:
        windowOpen = False
        output.servoToPosition(180)
        
# Turn heater on or off based on the action setting
def controlHeater(action):
    global heaterOn
    if (action == "on"):
        heaterOn = True
        output.highPowerOn(15)
    else:
        heaterOn = False
        output.highPowerOff(15)

# Initialise button checking and debounce timers (debouncing is important as it ensures only one button press is registered at a time, rather than multiple while a button held down)
debounceTimerA = Timer()
debounceTimerA.init(period=2, mode=Timer.PERIODIC, callback=checkButtonA)
debounceTimerB = Timer()
debounceTimerB.init(period=2, mode=Timer.PERIODIC, callback=checkButtonB)

buttonAState = 0 
buttonBState = 0

# Setup gas sensor and calculate baseline values
bme688.setupGasSensor()
bme688.calcBaselines()

# Start with the window closed
output.servoToPosition(180)

# Program always starts displaying the main menu
showMainMenu()

# Take and store initial sensor readings
bme688.measureData()
temp = bme688.readTemperature()
press = bme688.readPressure()
humid = bme688.readHumidity()
IAQ = bme688.getAirQualityScore()
CO2 = bme688.readeCO2()

# Setup data log file
log.writeProjectInfo("Smart House Data", "Climate Sensor Readings and Device Status Log")
log.nameColumnHeadings("Date", "Time", "Temperature", "Pressure", "Humidity", "IAQ", "eCO2", "Window Status", "Heater Status", "Light Status")

# This loop will run forever (or until power is lost to the Pico)
while True:
    # Remember the previous sensor readings for comparison
    prevTemp = temp
    prevPress = press
    prevHumid - humid
    prevIAQ = IAQ
    prevCO2 = CO2
    # Take and store new sensor readings
    bme688.measureData()
    temp = bme688.readTemperature()
    press = bme688.readPressure()
    humid = bme688.readHumidity()
    IAQ = bme688.getAirQualityScore()
    CO2 = bme688.readeCO2()
    # Refresh current display screen, if required, to show the latest data/status
    if (currentScreen == 1):
        showDataDisplay()
    elif (currentScreen == 2):
        showDeviceStatus()
    
    # Apply latest ZIP Stick light settings
    controlLights(lightSetting)
    
    # Test whether humidity is above/below threshold
    if (humid > HUMIDITY_THRESHOLD):
        humidHigh = True
    elif (humid <= HUMIDITY_THRESHOLD):
        humidHigh = False
    # Test whether temperature is above/below thresholds or in 'OK' range
    if (temp < TEMPERATURE_THRESHOLD_LOW):
        tempHigh = False
        tempLow = True
    elif ((temp >= TEMPERATURE_THRESHOLD_LOW) and (temp <= TEMPERATURE_THRESHOLD_HIGH)):
        tempHigh = False
        tempLow = False
    elif (temp > TEMPERATURE_THRESHOLD_HIGH):
        tempHigh = True
        tempHigh = False

    # Test whether IAQ and CO2 are above/below certain thresholds and set ZIP LEDs accordingly
    # IAQ
    if (IAQ < IAQ_THRESHOLD_MED):
        zipleds.setLED(0, zipleds.GREEN)
    elif ((IAQ >= IAQ_THRESHOLD_MED) and (IAQ < IAQ_THRESHOLD_HIGH)):
        zipleds.setLED(0, zipleds.YELLOW)
    elif (IAQ >= IAQ_THRESHOLD_HIGH):
        zipleds.setLED(0, zipleds.RED)
    # CO2
    if (CO2 < CO2_THRESHOLD_MED):
        zipleds.setLED(2, zipleds.GREEN)
    elif ((CO2 >= CO2_THRESHOLD_MED) and (CO2 < CO2_THRESHOLD_HIGH)):
        zipleds.setLED(2, zipleds.YELLOW)
    elif (CO2 >= CO2_THRESHOLD_HIGH):
        zipleds.setLED(2, zipleds.RED)
    zipleds.show()

    # Decide whether to open/close window and/or turn heater on/off based on humidity and temperature
    if tempLow:
        controlWindow("close")
        controlHeater("on")
    elif tempHigh:
        controlWindow("open")
        controlHeater("off")
    elif (not(tempLow) and not(tempHigh)):
        controlHeater("off")
        if humidHigh:
            controlWindow("open")

    # Once the hour for the ON or OFF time has passed, set the 'lightTimingControl' variable back to False ready for the next cycle
    if lightTimingControl:
        if ((rtc.readParameter("h") != LIGHT_ON_TIME) and (rtc.readParameter("h") != LIGHT_OFF_TIME)):
            lightTimingControl = False
    # Turn the lights on/off based on the time of day
    if not(lightTimingControl):
        if (rtc.readParameter("h") == LIGHT_ON_TIME):
            controlLights(0)
            lightTimingControl = True   # This makes sure that the program won't keep turing the lights on (or off below) if, for example, the user wants a different setting
        elif (rtc.readParameter("h") == LIGHT_OFF_TIME):
            controlLights(4)
            lightTimingControl = True

    # Log data every 30s
    if ((rtc.readParameter("s") % 30) == 0):
        log.storeDataEntry(rtc.readDateString(), rtc.readTimeString(), str(bme688.readTemperature()), str(bme688.readPressure()), str(bme688.readHumidity()), str(bme688.getAirQualityScore()), str(bme688.readeCO2()), windowStatus, heaterStatus, lightStatus)

