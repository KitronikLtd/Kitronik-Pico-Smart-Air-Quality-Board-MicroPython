# Kitronik-Pico-Smart-Air-Quality-Board-MicroPython
A module and sample code for the Kitronik Smart Air Quality Board for the Raspberry Pi Pico. (www.kitronik.co.uk/5336)
  
To use, save the PicoAirQuality.py file onto the Pico so it can be imported.  
There are several classes within the module for accessing and controlling the different board features.  
## Import PicoAirQuality.py and construct instances of the differenet classes:
```python
    from PicoAirQuality import KitronikBME688, KitronikOLED, KitronikRTC, KitronikZIPLEDs, KitronikBuzzer, KitronikDataLogger, KitronikOutputControl, KitronikButton

	bme688 = KitronikBME688()    # Class for using the BME688 air quality and environmental sensor
	oled = KitronikOLED()    # Class for using the OLED display screen
	rtc = KitronikRTC()    # Class for using the built-in Pico Real-Time Clock (RTC)
	zipleds = KitronikZIPLEDs(3)    # Class for using the ZIP LEDs (on-board and external connections)
	buzzer = KitronikBuzzer()    # Class for using the piezo buzzer
	log = KitronikDataLogger("data_log.txt", "semicolon")    # Class for using the built-in Pico file system for data logging
	output = KitronikOutputControl()    # Class for using the high-power and servo outputs
	buttons = KitronikButton()    # Class for using the input buttons
 ```
Below are explanations of the functions available in each class.  

## KitronikBME688
* Class instantiation reads and sets up all calibration parameters for compensation calculations
* setupGasSensor(targetTemp=300, heatDuration=150)
* calcBaselines()
* measureData()
* readTemperature(temperature_unit="C")
* readPressure(pressure_unit="Pa")
* readHumidity()
* readGasRes()
* readeCO2() - calls calcAirQuality()
* getAirQualityPercent() - calls calcAirQuality()
* getAirQualityScore() - calls calcAirQuality()

## KitronikOLED
* Class instantiation sets up defaults for the screen, including the correct orientation
* displayText(text, line, x_offset=0)
* show()
* plot(variable)
* drawLine(start_x, start_y, end_x, end_y)
* drawRect(start_x, start_y, width, height, fill=False)
* clear()
* poweroff()
* poweron()
* contrast(contrast)
* invert(invert)

## KitronikRTC
The Pico has an onboard RTC (Real-Time Clock) which has a very simple user interface enabling the setting or reading of the date and time.  
The KitronikRTC class expands this functionality, allowing separate setting of date and time, reading the date and time out as strings, reading individual date/time parameters and the ability to set alarms  
Set the date and time:  
```python
rtc.setDate(day, month, year)
rtc.setTime(hours, minutes, seconds)
```
Read the date and time as strings:  
```python
rtc.readDateString()    # DD/MM/YY
rtc.readTimeString()    # HH:MM:SS
```
Read individual date or time parameters:  
```python
rtc.readParameter(parameter)
```
'parameter' can be:  
* 'd' = Day
* 'm' = Month
* 'y' = Year
* 'h' = Hour
* 'min' = Minute
* 's' = Second
  
Set an alarm:
```python
rtc.setAlarm(hour, minute)
```
Check whether an alarm time condition has been met - this function returns 'True' if the alarm is triggered:  
```python
rtc.checkAlarm()
```
Stop the alarm triggering once the time condition has been met:  
```python
rtc.silenceAlarm()
```

## KitronikZIPLEDs
ZIP LEDs have a 2 stage operation...
### Setup ZIP LEDs:  
Set the LEDs with the colour required:  
```python
zipleds.setLED(whichLED, whichColour)
```
where:  
* whichLED => 0-2 for onboard ZIP LEDs (if further ZIP LEDs are connected to the ZIP LED extension, the full number will need to be included in the class instantiation)  
* whichColour => tuple of (Red Value, Green Value, Blue Value), or one of the pre-defined colours:
```python
COLOURS = (BLACK, RED, YELLOW, GREEN, CYAN, BLUE, PURPLE, WHITE)
```
Turn off the LEDs: 
```python
zipleds.clear(whichLED)
```
where:  
* whichLED => 0-2 for onboard ZIP LEDs

Control the brightness:
```python
zipleds.setBrightness(value)
```
where:  
* value => 0-100 (brightness value in %) 

### Make the changes visible:
```python
zipleds.show():
```

## KitronikBuzzer
The piezo buzzer on the board can play single frequency tones, with the pitch and tone length controlled by the following functions.  
Play a continous tone at a set frequency (in the range 30Hz to 3kHz):  
```python
buzzer.playTone(freq)
```
Play a tone at a set frequency for a set length of time (in milliseconds):  
```python
buzzer.playTone_Length(freq, length)
```
Stop the current tone sounding:  
```python
buzzer.stopTone()
```

## KitronikDataLogger
* On class instantiation, creates file with input name and assigns the separator between data fields
* Max file size set to 500000 (approx. 10000 entries)
* writeProjectInfo(name, subject)
* setupDataFields(field1 - field10)
* storeDataEntry(field1 - field10) - checks for file size and removes lines if neccessary
* eraseAllData()
 * deleteDataFile()

## KitronikOutputControl
### Servo:
The servo PWM (20ms repeat, on period capped between 500 and 2500us) is driven using the Pico PIO.  
The servos are registered automatically in the initalisation of the class.   
This process sets the PIO PWM active on the servo pin.  
If the pin is needed for another purpose it can be 'deregistered' which sets the PIO to inactive.  
 ```python
    robot.deregisterServo(servo)
 ```
To re-register a servo after it has been de-registered:  
```python
    robot.registerServo(servo)
```
where:
* servo => the servo number (0-3)

### High-Power Outputs
* Pins GP3 and GP15 are assigned as high-power outputs
* highPowerOn(pin)
* highPowerOff(pin)

## KitronikButton
* Class initialises two buttons (buttonA and buttonB) which can then be accessed in the main program file.
* They require an interrupt (IRQ) and a handler to be created.

### Button IRQ:
```python
buttons.buttonA.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonA_IRQHandler)
buttons.buttonB.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonB_IRQHandler)
```

### Button IRQ Handler:
```python
def ButtonA_IRQHandler(pin):
    oled.clear()
    bme688.measureData()
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
    
def ButtonB_IRQHandler(pin):
    oled.clear()
    oled.show()
    zipleds.clear(0)
    zipleds.clear(2)
    zipleds.show()
```

# Troubleshooting

This code is designed to be used as a module. See: https://kitronik.co.uk/blogs/resources/modules-micro-python-and-the-raspberry-pi-pico for more information

