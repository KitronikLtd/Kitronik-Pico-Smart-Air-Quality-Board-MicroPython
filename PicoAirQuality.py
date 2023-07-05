import math
import framebuf
import array
import os
from machine import Pin, PWM, ADC, time_pulse_us, I2C, RTC
from rp2 import PIO, StateMachine, asm_pio
from time import sleep, sleep_ms, sleep_us, ticks_ms, ticks_us
from micropython import const

# Initialise the module with all outputs off
# High Power Output Pins
hp_3 = Pin(3, Pin.OUT)
hp_15 = Pin(15, Pin.OUT)
hp_3.value(0)
hp_15.value(0)
# Servo
servo = Pin(2, Pin.OUT)
servo.value(0)
# Buzzer
buzzer = PWM(Pin(4))
buzzer.duty_u16(0)

# List of which StateMachines we have used
usedSM = [False, False, False, False, False, False, False, False]

# The KitronikButton class enable the use of the 2 user input buttons on the board
class KitronikButton:
    def __init__(self):
        self.buttonA = Pin(12, Pin.IN, Pin.PULL_DOWN)
        self.buttonB = Pin(13, Pin.IN, Pin.PULL_DOWN)

# The KitronikOutputControl class enables control of the servo and high-power outputs on the board
class KitronikOutputControl:
    # This code drives a pwm on the PIO. It is running at 2Mhz, which gives the PWM a 1uS resolution. 
    @asm_pio(sideset_init=PIO.OUT_LOW)
    def _servo_pwm():
    # First we clear the pin to zero, then load the registers. Y is always 20000 - 20uS, x is the pulse 'on' length.     
        pull(noblock) .side(0)
        mov(x, osr) # Keep most recent pull data stashed in X, for recycling by noblock
        mov(y, isr) # ISR must be preloaded with PWM count max
    # This is where the looping work is done. the overall loop rate is 1Mhz (clock is 2Mhz - we have 2 instructions to do)    
        label("loop")
        jmp(x_not_y, "skip") #if there is 'excess' Y number leave the pin alone and jump to the 'skip' label until we get to the X value
        nop()         .side(1)
        label("skip")
        jmp(y_dec, "loop") #count down y by 1 and jump to pwmloop. When y is 0 we will go back to the 'pull' command

    def __init__(self):
        # High Power Output Pins
        self.highPwr_3 = Pin(3, Pin.OUT)
        self.highPwr_15 = Pin(15, Pin.OUT)

        # Servo Control
        self.servo = []
        # Servo 0 degrees -> pulse of 0.5ms, 180 degrees 2.5ms
        # Pulse train freq 50hz - 20ms
        # 1us is freq of 1000000
        # Servo pulses range from 500 to 2500us and overall pulse train is 20000us repeat.
        # Servo is on GP2
        self.maxServoPulse = 2500
        self.minServoPulse = 500
        self.pulseTrain = 20000
        self.degreesToUS = 2000/180
        self.piEstimate = 3.1416

        # Create and start the servo statemachine
        for i in range(8): # StateMachine range from 0 to 7
            if usedSM[i]:
                continue # Ignore this index if already used
            try:
                self.servo.append(StateMachine(i, self._servo_pwm, freq=2000000, sideset_base=Pin(2)))
                usedSM[i] = True # Set this index to used
                break # Have claimed the SM, can leave now
            except ValueError:
                pass # External resouce has SM, move on
            if i == 7:
                # Cannot find an unused SM
                raise ValueError("Could not claim a StateMachine, all in use")
        
        self.servo[0].put(self.pulseTrain)
        self.servo[0].exec("pull()")
        self.servo[0].exec("mov(isr, osr)")
        self.servo[0].put(self.minServoPulse)
        self.registerServo()

    # Doesn't actually register/unregister, just stops and starts the servo PIO
    # The servo is registered by default in the __init__() function - these are only required if you want to use Pin 2 for something else, and then register the servo again
    def registerServo(self):
        if(not self.servo[0].active()):
            self.servo[0].active(1)

    def deregisterServo(self):
        if(self.servo[0].active()):
            self.servo[0].active(0)
 
    # goToPosition takes a degree position for the servo to go to. 
    # 0degrees->180 degrees is 0->2000us, plus offset of 500uS
    # 1 degree ~ 11uS.
    # This function does the sum then calls goToPeriod to actually poke the PIO 
    def servoToPosition(self, degrees):
        pulseLength = int(degrees*self.degreesToUS + 500)
        self.servoToPeriod(pulseLength)
    
    # Takes the angle in radians to move the servo to.
    # 0 radians to 3.1416
    def servoToRadians(self, radians):
        period = int((radians / self.piEstimate) * 2000) + 500
        self.servoToPeriod(period)
    
    def servoToPeriod(self, period):
        if(period < 500):
            period = 500
        if(period >2500):
            period =2500
        self.servo[0].put(period)

    # Functions to turn on/off the high power outputs
    # Enter the pin number, either '3' or '15'
    def highPowerOn(self, pin):
        if (pin == 3):
            self.highPwr_3.value(1)
        elif (pin == 15):
            self.highPwr_15.value(1)

    def highPowerOff(self, pin):
        if (pin == 3):
            self.highPwr_3.value(0)
        elif (pin == 15):
            self.highPwr_15.value(0)

# The KitronikDataLogger class enables data logging through the Pico file system
# It is possible to create multiple data logger instances to then log to multiple files simulataneously
class KitronikDataLogger:
    # Function is called when the class is initialised - sets the maximum permissable filesize, the data separator and creates the log file with the entered filename
    # Separator options: ("comma", "semicolon", "tab")
    def __init__(self, file = "data_log.txt", separator = "semicolon"):
        self.MAX_FILE_SIZE = 500000 # This is approximately 10000 full entries
        if (separator == "comma"):
            self.SEPARATOR = ","
        elif (separator == "semicolon"):
            self.SEPARATOR = ";"
        elif (separator == "tab"):
            self.SEPARATOR = "\t"
        self.FILENAME = file
        try:
            f = open(self.FILENAME, "x")
            f.close()
        except OSError:
            print("File already exists")
        self.line1 = ""
        self.line2 = ""
        self.line3 = ""
        self.dataHeadings = ""
        self.projectInfo = False
        self.headings = False

    # Write a header section to the specified file (there are 3 free text fields, each will write on a separate line)
    def writeProjectInfo(self, line1="", line2="", line3=""):
        if (line1 != ""):
            self.writeFile(self.FILENAME, line1 + "\r\n")
            self.line1 = line1
        if (line2 != ""):
            self.writeFile(self.FILENAME, line2 + "\r\n")
            self.line2 = line2
        if (line3 != ""):
            self.writeFile(self.FILENAME, line3 + "\r\n")
            self.line3 = line3
        self.projectInfo = True

    # This writes whatever is passed to it to the file     
    def writeFile(self, file, passed):
        f = open(file, "a") #open in append - creates if not existing, will append if it exists
        f.write(passed)
        f.close()

    # Input and write to the file up to 10 data field headings
    def nameColumnHeadings(self, field1="", field2="", field3="", field4="", field5="", field6="", field7="", field8="", field9="", field10=""):
        dataHeadings = ""
        if (field1 != ""):
            dataHeadings = field1 + self.SEPARATOR
        if (field2 != ""):
            dataHeadings = dataHeadings + field2 + self.SEPARATOR
        if (field3 != ""):
            dataHeadings = dataHeadings + field3 + self.SEPARATOR
        if (field4 != ""):
            dataHeadings = dataHeadings + field4 + self.SEPARATOR
        if (field5 != ""):
            dataHeadings = dataHeadings + field5 + self.SEPARATOR
        if (field6 != ""):
            dataHeadings = dataHeadings + field6 + self.SEPARATOR
        if (field7 != ""):
            dataHeadings = dataHeadings + field7 + self.SEPARATOR
        if (field8 != ""):
            dataHeadings = dataHeadings + field8 + self.SEPARATOR
        if (field9 != ""):
            dataHeadings = dataHeadings + field9 + self.SEPARATOR
        if (field10 != ""):
            dataHeadings = dataHeadings + field10 + self.SEPARATOR

        self.dataHeadings = dataHeadings
        self.writeFile(self.FILENAME, dataHeadings + "\r\n")
        self.headings = True

    # Store up to 10 data entries (match the order with the data headings used)
    def storeDataEntry(self, field1="", field2="", field3="", field4="", field5="", field6="", field7="", field8="", field9="", field10=""):
        dataEntry = ""
        if (field1 != ""):
            dataEntry = field1 + self.SEPARATOR
        if (field2 != ""):
            dataEntry = dataEntry + field2 + self.SEPARATOR
        if (field3 != ""):
            dataEntry = dataEntry + field3 + self.SEPARATOR
        if (field4 != ""):
            dataEntry = dataEntry + field4 + self.SEPARATOR
        if (field5 != ""):
            dataEntry = dataEntry + field5 + self.SEPARATOR
        if (field6 != ""):
            dataEntry = dataEntry + field6 + self.SEPARATOR
        if (field7 != ""):
            dataEntry = dataEntry + field7 + self.SEPARATOR
        if (field8 != ""):
            dataEntry = dataEntry + field8 + self.SEPARATOR
        if (field9 != ""):
            dataEntry = dataEntry + field9 + self.SEPARATOR
        if (field10 != ""):
            dataEntry = dataEntry + field10 + self.SEPARATOR

        while (self.checkFileSize() > self.MAX_FILE_SIZE):
            self.removeOneLine()

        self.writeFile(self.FILENAME, dataEntry + "\r\n")

    # This returns the size of the file, or 0 if the file does not exist
    def checkFileSize(self):
        # f is a file-like object.
        try:
            f = open(self.FILENAME, "r") # Open read - this throws an error if file does not exist - in that case the size is 0
            f.seek(0, 2)
            size = f.tell()
            f.close()
            return size
        except:
            # if we wanted to know we could print some diagnostics here like:
            #print("Exception - File does not exist")
            return 0 

    # Remove a line from the data file to make space for more data
    def removeOneLine(self):
        tempName = self.FILENAME + ".bak"
        readFrom = open(self.FILENAME, "r")
        writeTo = open(tempName, "w")
        if self.projectInfo:        # If there is Project Info, skip over these lines and then write them to the temporary file
            for l in range(3):
                readFrom.readline()
            writeTo.write(self.line1 + "\r\n")
            writeTo.write(self.line2 + "\r\n")
            writeTo.write(self.line3  + "\r\n")
        if self.headings:
            readFrom.readline()     # If there are Headings, skip over this line and then write them to the temporary file
            writeTo.write(self.dataHeadings  + "\r\n")
        readFrom.readline()         # Read and throw away the first line of data in the file

        for lines in readFrom:      # Write the remaining lines to the temporary file
            writeTo.write(lines)
        readFrom.close()    # Close both files
        writeTo.close()
        os.remove(self.FILENAME)    # Delete original log file
        os.rename(tempName, self.FILENAME)  # Rename temporary file as new log file (now with the first line of data removed)

    # Deletes all the contents of the file
    def eraseAllData(self):
        f = open(self.FILENAME, "w")
        f.write("")
        f.close()

    # Deletes the file from the Pico file system
    def deleteDataFile(self):
        os.remove(self.FILENAME)

# The KitronikBuzzer class enables control of the piezo buzzer on the board
class KitronikBuzzer:
    # Function is called when the class is initialised and sets the buzzer pin to GP4
    def __init__(self):
        self.buzzer = PWM(Pin(4))
        self.dutyCycle = 32767

    # Play a continous tone at a specified frequency
    def playTone(self, freq):
        if (freq < 30):
            freq = 30
        if (freq > 3000):
            freq = 3000
        self.buzzer.freq(freq)
        self.buzzer.duty_u16(self.dutyCycle)

    # Play a tone at a speciied frequency for a specified length of time in ms
    def playTone_Length(self, freq, length):
        self.playTone(freq)
        sleep_ms(length)
        self.stopTone()

    # Stop the buzzer producing a tone
    def stopTone(self):
        self.buzzer.duty_u16(0)

# The KitronikZIPLEDs class enables control of the ZIP LEDs both on the board and any connected externally
class KitronikZIPLEDs:
    # We drive the ZIP LEDs using one of the PIO statemachines.         
    @asm_pio(sideset_init=PIO.OUT_LOW, out_shiftdir=PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
    def _ZIPLEDOutput():
        T1 = 2
        T2 = 5
        T3 = 3
        wrap_target()
        label("bitloop")
        out(x, 1)               .side(0)    [T3 - 1]
        jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
        jmp("bitloop")          .side(1)    [T2 - 1]
        label("do_zero")
        nop()                   .side(0)    [T2 - 1]
        wrap()

    def __init__(self, num_zip_leds):
        self.num_zip_leds = num_zip_leds
        
        # Create  and start the StateMachine for the ZIPLeds
        for i in range(8): # StateMachine range from 0 to 7
            if usedSM[i]:
                continue # Ignore this index if already used
            try:
                self.ZIPLEDs = StateMachine(i, self._ZIPLEDOutput, freq=8_000_000, sideset_base=Pin(20))
                usedSM[i] = True # Set this index to used
                break # Have claimed the SM, can leave now
            except ValueError:
                pass # External resouce has SM, move on
            if i == 7:
                # Cannot find an unused SM
                raise ValueError("Could not claim a StateMachine, all in use")
        
        self.theLEDs = array.array("I", [0 for _ in range(self.num_zip_leds)]) #an array for the LED colours.
        self.brightness = 0.5 #20% initially 
        self.ZIPLEDs.active(1)
            
        # Define some colour tuples for people to use.    
        self.BLACK = (0, 0, 0)
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 150, 0)
        self.GREEN = (0, 255, 0)
        self.CYAN = (0, 255, 255)
        self.BLUE = (0, 0, 255)
        self.PURPLE = (180, 0, 255)
        self.WHITE = (255, 255, 255)
        self.COLOURS = (self.BLACK, self.RED, self.YELLOW, self.GREEN, self.CYAN, self.BLUE, self.PURPLE, self.WHITE)

    # Show pushes the current setup of the LEDS to the physical LEDS - it makes them visible.
    def show(self):
        brightAdjustedLEDs = array.array("I", [0 for _ in range(self.num_zip_leds)])
        for i,c in enumerate(self.theLEDs):
            r = int(((c >> 8) & 0xFF) * self.brightness)
            g = int(((c >> 16) & 0xFF) * self.brightness)
            b = int((c & 0xFF) * self.brightness)
            brightAdjustedLEDs[i] = (g<<16) + (r<<8) + b
        self.ZIPLEDs.put(brightAdjustedLEDs, 8)

    # Turn the LED off by setting the colour to black
    def clear(self, whichLED):
        self.setLED(whichLED, self.BLACK)
        
    # Sets the colour of an individual LED. Use show to make change visible
    def setLED(self, whichLED, whichColour):
        if(whichLED<0):
            raise Exception("INVALID LED:",whichLED," specified")
        elif(whichLED>(self.num_zip_leds - 1)):
            raise Exception("INVALID LED:",whichLED," specified")
        else:
            self.theLEDs[whichLED] = (whichColour[1]<<16) + (whichColour[0]<<8) + whichColour[2]

    # Gets the stored colour of an individual LED, which isnt nessecerily the colour on show if it has been changed, but not 'show'n
    def getLED(self, whichLED):
        if(whichLED<0):
            raise Exception("INVALID LED:",whichLED," specified")
        elif(whichLED>(self.num_zip_leds - 1)):
            raise Exception("INVALID LED:",whichLED," specified")
        else:
            return(((self.theLEDs[whichLED]>>8) & 0xff), ((self.theLEDs[whichLED]>>16)& 0xff) ,((self.theLEDs[whichLED])& 0xff))

    # Takes 0-100 as a brightness value, brighness is applies in the'show' function
    def setBrightness(self, value):
            #cap to 0-100%
        if (value<0):
            value = 0
        elif (value>100):
            value=100
        self.brightness = value / 100

# The KitronikRTC class enables use of the Pico RTC
class KitronikRTC:
    # Function is called when the class is initialised and creates an instance of the Pico RTC and defines all the global variables
    def __init__(self):
        self.rtc = RTC()
        self.day = 0
        self.month = 0
        self.year = 0
        self.weekday = 0    # In range 0 - 6, 0 = Monday, 6 = Sunday
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.alarmHour = 0
        self.alarmMinute = 0
        self.alarmSet = False
        self.alarmTrigger = False
        self.alarmRepeat = False
        self.hourPeriod = 0
        self.minutePeriod = 0

    # Function calculates the weekday (0 = Monday, 6 = Sunday) based on the date, taking into account leap years
    def calcWeekday(self, day, month, year):
        dayOffset = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
        if (month < 3):
            month = month - 1

        self.weekday = (year + (year // 4) - (year // 100) + (year // 400) + dayOffset[month - 1] + day) % 7    # Returns 0 - 6, 0 = Sunday, 6 = Saturday
        if (self.weekday == 0):
            self.weekday = 6
        else:
            self.weekday = self.weekday - 1

    # Set the date on the Pico RTC
    def setDate(self, day, month, year):
        self.getDateTime()
        self.calcWeekday(day, month, year)
        self.rtc.datetime((year, month, day, self.weekday, self.hour, self.minute, self.second, 0))

    # Set the time on the Pico RTC
    def setTime(self, hours, minutes, seconds):
        self.getDateTime()
        self.rtc.datetime((self.year, self.month, self.day, self.weekday, hours, minutes, seconds, 0))

    # Return the current date and time
    def getDateTime(self):
        newDateTime = self.rtc.datetime()
        self.day = newDateTime[2]
        self.month = newDateTime[1]
        self.year = newDateTime[0]
        self.weekday = newDateTime[3]
        self.hour = newDateTime[4]
        self.minute = newDateTime[5]
        self.second = newDateTime[6]

    # Return the current date as a string
    def readDateString(self):
        self.getDateTime()
        if (self.day < 10):
            day = "0" + str(self.day)
        else:
            day = str(self.day)

        if (self.month < 10):
            month = "0" + str(self.month)
        else:
            month = str(self.month)

        date = day + "/" + month + "/" + str(self.year)
        return date

    # Return the current time as a string
    def readTimeString(self):
        self.getDateTime()
        if (self.hour < 10):
            hour = "0" + str(self.hour)
        else:
            hour = str(self.hour)

        if (self.minute < 10):
            minute = "0" + str(self.minute)
        else:
            minute = str(self.minute)

        if (self.second < 10):
            second = "0" + str(self.second)
        else:
            second = str(self.second)

        time = hour + ":" + minute + ":" + second
        return time

    # Return a specific date/time parameter as a number
    # d = day, m = month, y = year, h = hour, min = minute, s = second
    def readParameter(self, parameter):
        self.getDateTime()
        if (parameter == "d"):
            return self.day
        elif (parameter == "m"):
            return self.month
        elif (parameter == "y"):
            return self.year
        elif (parameter == "h"):
            return self.hour
        elif (parameter == "min"):
            return self.minute
        elif (parameter == "s"):
            return self.second

    # Set an alarm for a specific hour and minute
    # Extra options to set a periodically repeating alarm (set alarmRepeat to True and then specifiy the hour and/or minute period between alarms)
    def setAlarm(self, hour, minute, alarmRepeat=False, hourPeriod=0, minutePeriod=0):
        self.alarmHour = math.ceil(hour)
        self.alarmMinute = math.ceil(minute)
        self.alarmRepeat = alarmRepeat
        
        if alarmRepeat:
            self.hourPeriod = math.ceil(hourPeriod)
            self.minutePeriod = math.ceil(minutePeriod)
        self.alarmSet = True

    # Check whether the alarm conditions have been met and then trigger the alarm
    def checkAlarm(self):
        if self.alarmSet:
            if (self.readParameter("h") == self.alarmHour):
                if (self.readParameter("min") == self.alarmMinute):
                    self.alarmTrigger = True
        return self.alarmTrigger

    # Sets 'alarmTrigger' back to False, checks whether the alarm should repeat (sets new one if it should) or sets 'alarmSet' back to False
    def silenceAlarm(self):
        self.alarmTrigger = False
        if not self.alarmRepeat:
            self.alarmSet = False
        else:
            newHour = self.alarmHour + self.hourPeriod
            newMinute = self.alarmMinute + self.minutePeriod
            if (newMinute > 59):
                newMinute = newMinute - 60
                newHour = newHour + 1
            if (newHour > 23):
                newHour = newHour - 24
            self.setAlarm(newHour, newMinute, True, self.hourPeriod, self.minutePeriod)

# The KitronikBME688 class enables contro and use of the BME688 sensor on the board
class KitronikBME688:
    # The following functions are for reading the registers on the BME688
    # Function for reading register as signed 8 bit integer
    def getUInt8(self, reg):
        return int.from_bytes(self.i2c.readfrom_mem(self.CHIP_ADDRESS, reg, 1), "big")
    
    # Function to convert unsigned ints to twos complement signed ints
    def twosComp(self, value, bits):
        if ((value & (1 << (bits - 1))) != 0):
            value = value - (1 << bits)
        return value

    # Function for proportionally mapping a value to a different value range
    def mapValues(self, value, frMin, frMax, toMin, toMax):
        toRange = toMax - toMin
        mappedVal = toMin + ((value - frMin) * ((toMax - toMin) / (frMax - frMin)))
        return mappedVal

    def __init__(self, i2cAddr=0x77, sda=6, scl=7):
        self.CHIP_ADDRESS = i2cAddr    # I2C address as determined by hardware configuration
        sda = Pin(sda)
        scl = Pin(scl)
        self.i2c = I2C(1, sda=sda, scl=scl, freq=100_000, timeout=100_000)

        # Useful BME688 Register Addresses
        # Control
        self.CTRL_MEAS = 0x74       # Bit position <7:5>: Temperature oversampling   Bit position <4:2>: Pressure oversampling   Bit position <1:0>: Sensor power mode
        self.RESET = 0xE0           # Write 0xB6 to initiate soft-reset (same effect as power-on reset)
        self.CHIP_ID = 0xD0         # Read this to return the chip ID: 0x61 - good way to check communication is occurring
        self.CTRL_HUM = 0x72        # Bit position <2:0>: Humidity oversampling settings
        self.CONFIG = 0x75          # Bit position <4:2>: IIR filter settings
        self.CTRL_GAS_0 = 0x70      # Bit position <3>: Heater off (set to '1' to turn off current injection)
        self.CTRL_GAS_1 = 0x71      # Bit position <5> DATASHEET ERROR: Enable gas conversions to start when set to '1'   Bit position <3:0>: Heater step selection (0 to 9)

        # Pressure Data
        self.PRESS_MSB_0 = 0x1F     # Forced & Parallel: MSB [19:12]
        self.PRESS_LSB_0 = 0x20     # Forced & Parallel: LSB [11:4]
        self.PRESS_XLSB_0 = 0x21    # Forced & Parallel: XLSB [3:0]

        # Temperature Data
        self.TEMP_MSB_0 = 0x22      # Forced & Parallel: MSB [19:12]
        self.TEMP_LSB_0 = 0x23      # Forced & Parallel: LSB [11:4]
        self.TEMP_XLSB_0 = 0x24     # Forced & Parallel: XLSB [3:0]

        # Humidity Data
        self.HUMID_MSB_0 = 0x25     # Forced & Parallel: MSB [15:8]
        self.HUMID_LSB_0 = 0x26     # Forced & Parallel: LSB [7:0]

        # Gas Resistance Data
        self.GAS_RES_MSB_0 = 0x2C   # Forced & Parallel: MSB [9:2]
        self.GAS_RES_LSB_0 = 0x2D   # Forced & Parallel: Bit <7:6>: LSB [1:0]    Bit <5>: Gas valid    Bit <4>: Heater stability    Bit <3:0>: Gas resistance range

        # Status
        self.MEAS_STATUS_0 = 0x1D   # Forced & Parallel: Bit <7>: New data    Bit <6>: Gas measuring    Bit <5>: Measuring    Bit <3:0>: Gas measurement index

        # Calibration parameters for compensation calculations
        # Temperature
        self.PAR_T1 = self.twosComp((self.getUInt8(0xEA) << 8) | self.getUInt8(0xE9), 16)      # Signed 16-bit
        self.PAR_T2 = self.twosComp((self.getUInt8(0x8B) << 8) | self.getUInt8(0x8A), 16)      # Signed 16-bit
        self.PAR_T3 = self.twosComp(self.getUInt8(0x8C), 8)           # Signed 8-bit

        # Pressure
        self.PAR_P1 = (self.getUInt8(0x8F) << 8) | self.getUInt8(0x8E)   # Always a positive number, do not do twosComp() conversion!
        self.PAR_P2 = self.twosComp((self.getUInt8(0x91) << 8) | self.getUInt8(0x90), 16)      # Signed 16-bit
        self.PAR_P3 = self.twosComp(self.getUInt8(0x92), 8)                                 # Signed 8-bit
        self.PAR_P4 = self.twosComp((self.getUInt8(0x95) << 8) | self.getUInt8(0x94), 16)      # Signed 16-bit
        self.PAR_P5 = self.twosComp((self.getUInt8(0x97) << 8) | self.getUInt8(0x96), 16)      # Signed 16-bit
        self.PAR_P6 = self.twosComp(self.getUInt8(0x99), 8)                                 # Signed 8-bit
        self.PAR_P7 = self.twosComp(self.getUInt8(0x98), 8)                                 # Signed 8-bit
        self.PAR_P8 = self.twosComp((self.getUInt8(0x9D) << 8) | self.getUInt8(0x9C), 16)      # Signed 16-bit
        self.PAR_P9 = self.twosComp((self.getUInt8(0x9F) << 8) | self.getUInt8(0x9E), 16)      # Signed 16-bit
        self.PAR_P10 = self.twosComp(self.getUInt8(0xA0), 8)                                # Signed 8-bit

        # Humidity
        parH1_LSB_parH2_LSB = self.getUInt8(0xE2)
        self.PAR_H1 = (self.getUInt8(0xE3) << 4) | (parH1_LSB_parH2_LSB & 0x0F)
        self.PAR_H2 = (self.getUInt8(0xE1) << 4) | (parH1_LSB_parH2_LSB >> 4)
        self.PAR_H3 = self.twosComp(self.getUInt8(0xE4), 8)                                 # Signed 8-bit
        self.PAR_H4 = self.twosComp(self.getUInt8(0xE5), 8)                                 # Signed 8-bit
        self.PAR_H5 = self.twosComp(self.getUInt8(0xE6), 8)                                 # Signed 8-bit
        self.PAR_H6 = self.twosComp(self.getUInt8(0xE7), 8)                                 # Signed 8-bit
        self.PAR_H7 = self.twosComp(self.getUInt8(0xE8), 8)                                 # Signed 8-bit

        # Gas resistance
        self.PAR_G1 = self.twosComp(self.getUInt8(0xED), 8)                                 # Signed 8-bit
        self.PAR_G2 = self.twosComp((self.getUInt8(0xEB) << 8) | self.getUInt8(0xEC), 16)      # Signed 16-bit
        self.PAR_G3 = self.getUInt8(0xEE)                                # Unsigned 8-bit
        self.RES_HEAT_RANGE = (self.getUInt8(0x02) >> 4) & 0x03
        self.RES_HEAT_VAL = self.twosComp(self.getUInt8(0x00), 8)              # Signed 8-bit

        # Oversampling rate constants
        self.OSRS_1X = 0x01
        self.OSRS_2X = 0x02
        self.OSRS_4X = 0x03
        self.OSRS_8X = 0x04
        self.OSRS_16X = 0x05

        # IIR filter coefficient values
        self.IIR_0 = 0x00
        self.IIR_1 = 0x01
        self.IIR_3 = 0x02
        self.IIR_7 = 0x03
        self.IIR_15 = 0x04
        self.IIR_31 = 0x05
        self.IIR_63 = 0x06
        self.IIR_127 = 0x07

        #Global variables used for storing one copy of value, these are used in multiple locations for calculations
        self.bme688InitFlag = False
        self.gasInit = False

        self.tRead = 0       # calculated readings of sensor parameters from raw adc readings
        self.pRead = 0
        self.hRead = 0
        self.gRes = 0
        self.iaqPercent = 0
        self.iaqScore = 0
        self.airQualityRating = ""
        self.eCO2Value = 0

        self.gBase = 0
        self.hBase = 40        # Between 30% & 50% is a widely recognised optimal indoor humidity, 40% is a good middle ground
        self.hWeight = 0.25     # Humidity contributes 25% to the IAQ score, gas resistance is 75%
        self.hPrev = 0
        self.measTime = 0
        self.measTimePrev = 0

        self.tRaw = 0    # adc reading of raw temperature
        self.pRaw = 0       # adc reading of raw pressure
        self.hRaw = 0       # adc reading of raw humidity
        self.gResRaw = 0  # adc reading of raw gas resistance
        self.gasRange = 0

        self.t_fine = 0                          # Intermediate temperature value used for pressure calculation
        self.newAmbTemp = 0
        self.tAmbient = 0       # Intermediate temperature value used for heater calculation
        self.ambTempFlag = False

        # Create an instance of the OLED display screen for use during setup and for error messages
        self.screen = KitronikOLED()

        # Begin the hardware inititialisation for the BME688 sensor
        self.bme688Init()

    # Temperature compensation calculation: rawADC to degrees C (integer)
    def calcTemperature(self, tempADC):
        var1 = (tempADC >> 3) - (self.PAR_T1 << 1)
        var2 = (var1 * self.PAR_T2) >> 11
        var3 = ((((var1 >> 1) * (var1 >> 1)) >> 12) * (self.PAR_T3 << 4)) >> 14
        self.t_fine = var2 + var3
        self.newAmbTemp = ((self.t_fine * 5) + 128) >> 8
        self.tRead = self.newAmbTemp / 100     # Convert to floating point with 2 dp
        if (self.ambTempFlag == False):
            self.tAmbient = self.newAmbTemp

    # Pressure compensation calculation: rawADC to Pascals (integer)
    def intCalcPressure(self, pressureADC):
        var1 = (self.t_fine >> 1) - 64000
        var2 = ((((var1 >> 2) * (var1 >> 2)) >> 11) * self.PAR_P6) >> 2
        var2 = var2 + ((var1 * self.PAR_P5) << 1)
        var2 = (var2 >> 2) + (self.PAR_P4 << 16)
        var1 = (((((var1 >> 2) * (var1 >> 2)) >> 13) * (self.PAR_P3 << 5)) >> 3) + ((self.PAR_P2 * var1) >> 1)
        var1 = var1 >> 18
        var1 = ((32768 + var1) * self.PAR_P1) >> 15
        self.pRead = 1048576 - pressureADC
        self.pRead = ((self.pRead - (var2 >> 12)) * 3125)

        if (self.pRead >= (1 << 30)):
            self.pRead = (self.pRead // var1) << 1
        else:
            self.pRead = ((self.pRead << 1) // var1)

        var1 = (self.PAR_P9 * (((self.pRead >> 3) * (self.pRead >> 3)) >> 13)) >> 12
        var2 = ((self.pRead >> 2) * self.PAR_P8) >> 13
        var3 = ((self.pRead >> 8) * (self.pRead >> 8) * (self.pRead >> 8) * self.PAR_P10) >> 17
        self.pRead = self.pRead + ((var1 + var2 + var3 + (self.PAR_P7 << 7)) >> 4)

    # Humidity compensation calculation: rawADC to % (integer)
    # 'tempScaled' is the current reading from the Temperature sensor
    def intCalcHumidity(self, humidADC, tempScaled):
        self.hPrev = self.hRead
        tempScaled = math.trunc(tempScaled)
        
        var1 = humidADC - (self.PAR_H1 << 4) - (((tempScaled * self.PAR_H3) // 100) >> 1)
        var2 = (self.PAR_H2 * (((tempScaled * self.PAR_H4) // 100) + (((tempScaled * ((tempScaled * self.PAR_H5) // 100)) >> 6) // 100) + (1 << 14))) >> 10
        var3 = var1 * var2
        var4 = ((self.PAR_H6 << 7) + ((tempScaled * self.PAR_H7) // 100)) >> 4
        var5 = ((var3 >> 14) * (var3 >> 14)) >> 10
        var6 = (var4 * var5) >> 1
        self.hRead = (var3 + var6) >> 12
        self.hRead = (((var3 + var6) >> 10) * (1000)) >> 12
        self.hRead = self.hRead // 1000

    # Gas sensor heater target temperature to target resistance calculation
    # 'ambientTemp' is reading from Temperature sensor in degC (could be averaged over a day when there is enough data?)
    # 'targetTemp' is the desired temperature of the hot plate in degC (in range 200 to 400)
    # Note: Heating duration also needs to be specified for each heating step in 'gas_wait' registers
    def intConvertGasTargetTemp(self, ambientTemp, targetTemp):
        var1 = int((ambientTemp * self.PAR_G3) // 1000) << 8    # Divide by 1000 as we have ambientTemp in pre-degC format (i.e. 2500 rather than 25.00 degC)
        var2 = (self.PAR_G1 + 784) * (((((self.PAR_G2 + 154009) * targetTemp * 5) // 100) + 3276800) // 10)
        var3 = var1 + (var2 >> 1)
        var4 = (var3 // (self.RES_HEAT_RANGE + 4))
        var5 = (131 * self.RES_HEAT_VAL) + 65536                 # Target heater resistance in Ohms
        resHeatX100 = (((var4 // var5) - 250) * 34)
        resHeat = ((resHeatX100 + 50) // 100)

        return resHeat

    # Gas resistance compensation calculation: rawADC & range to Ohms (integer)
    def intCalcgRes(self, gasADC, gasRange):
        var1 = 262144 >> gasRange
        var2 = gasADC - 512
        var2 = var2 * 3
        var2 = 4096 + var2
        calcGasRes = ((10000 * var1) // var2)
        self.gRes = calcGasRes * 100

    # Initialise the BME688, establishing communication, entering initial T, P & H oversampling rates, setup filter and do a first data reading (won't return gas)
    def bme688Init(self):
        # Establish communication with BME688
        chipID = self.i2c.readfrom_mem(self.CHIP_ADDRESS, self.CHIP_ID, 1)
        chipID = int.from_bytes(chipID, "big")
        while (chipID != 97):
            chipID = self.i2c.readfrom_mem(self.CHIP_ADDRESS, self.CHIP_ID, 1)
        # Do a soft reset
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.RESET, "\xB6")
        sleep_ms(1000)
        # Set mode to SLEEP MODE: CTRL_MEAS reg <1:0>
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CTRL_MEAS, "\x00")
        # Set the oversampling rates for Temperature, Pressure and Humidity
        # Humidity: CTRL_HUM bits <2:0>
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CTRL_HUM, str(self.OSRS_2X))
        # Temperature: CTRL_MEAS bits <7:5>     Pressure: CTRL_MEAS bits <4:2>    (Combine and write both in one command)
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CTRL_MEAS, str(((self.OSRS_2X << 5) | (self.OSRS_16X << 2))))

        # IIR Filter: CONFIG bits <4:2>
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CONFIG, str(self.IIR_3 << 2))

        # Enable gas conversion: CTRL_GAS_1 bit <5>    (although datasheet says <4> - not sure what's going on here...)
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CTRL_GAS_1, "\x20")
        self.bme688InitFlag = True

        # Do an initial data read (will only return temperature, pressure and humidity as no gas sensor parameters have been set)
        self.measureData()

    # Setup the gas sensor (defaults are 300°C and 180ms).
    # targetTemp is the target temperature for the gas sensor plate to reach (200 - 400°C), eg: 300
    # heatDuration is the length of time for the heater to be turned on (0 - 4032ms), eg: 180
    # WARNING: The temperature and duration values can be changed but this is not recommended unless the user is familiar with gas sensor setup
    # The default values have been chosen as they provide a good all-round sensor response for air quality purposes
    def setupGasSensor(self, targetTemp=300, heatDuration=180):
        if (self.bme688InitFlag == False):
            self.bme688Init()

        # Limit targetTemp between 200°C & 400°C
        if (targetTemp < 200):
            targetTemp = 200
        elif (targetTemp > 400):
            targetTemp = 400

        # Limit heatDuration between 0ms and 4032ms
        if (heatDuration < 0):
            heatDuration = 0
        elif (heatDuration > 4032):
            heatDuration = 4032

        # Define the target heater resistance from temperature
        self.i2c.writeto_mem(self.CHIP_ADDRESS, 0x5A, self.intConvertGasTargetTemp(self.tAmbient, targetTemp).to_bytes(1, 'big'))   # res_wait_0 register - heater step 0

        # Define the heater on time, converting ms to register code (Heater Step 0) - cannot be greater than 4032ms
        # Bits <7:6> are a multiplier (1, 4, 16 or 64 times)    Bits <5:0> are 1ms steps (0 to 63ms)
        codedDuration = 0
        if (heatDuration < 4032):
            factor = 0
            while (heatDuration > 63):
                heatDuration = (heatDuration // 4)
                factor = factor + 1

            codedDuration = heatDuration + (factor * 64)
        else:
            codedDuration = 255

        self.i2c.writeto_mem(self.CHIP_ADDRESS, 0x64, codedDuration.to_bytes(1, 'big'))     # gas_wait_0 register - heater step 0

        # Select index of heater step (0 to 9): CTRL_GAS_1 reg <3:0>    (Make sure to combine with gas enable setting already there)
        gasEnable = self.getUInt8(self.CTRL_GAS_1) & 0x20
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CTRL_GAS_1, (0x00 | gasEnable).to_bytes(1, 'big'))   # Select heater step 0

        self.gasInit = True

    # Run all measurements on the BME688: Temperature, Pressure, Humidity & Gas Resistance.
    def measureData(self):
        if (self.bme688InitFlag == False):
            self.bme688Init()

        self.measTimePrev = self.measTime       # Store previous measurement time (ms since micro:bit powered on)

        # Set mode to FORCED MODE to begin single read cycle: CTRL_MEAS reg <1:0>    (Make sure to combine with temp/pressure oversampling settings already there)
        oSampleTP = self.getUInt8(self.CTRL_MEAS)
        self.i2c.writeto_mem(self.CHIP_ADDRESS, self.CTRL_MEAS, str((0x01 | oSampleTP)))

        # Check New Data bit to see if values have been measured: MEAS_STATUS_0 bit <7>
        newData = (self.getUInt8(self.MEAS_STATUS_0) & 0x80) >> 7
        while (newData != 1):
            newData = (self.getUInt8(self.MEAS_STATUS_0) & 0x80) >> 7

        # Check Heater Stability Status bit to see if gas values have been measured: <4> (heater stability)
        heaterStable = (self.getUInt8(self.GAS_RES_LSB_0) & 0x10) >> 4

        # If there is new data, read temperature ADC registers(this is required for all other calculations)        
        self.tRaw = (self.getUInt8(self.TEMP_MSB_0) << 12) | (self.getUInt8(self.TEMP_LSB_0) << 4) | (self.getUInt8(self.TEMP_XLSB_0) >> 4)

        # Read pressure ADC registers
        self.pRaw = (self.getUInt8(self.PRESS_MSB_0) << 12) | (self.getUInt8(self.PRESS_LSB_0) << 4) | (self.getUInt8(self.PRESS_XLSB_0) >> 4)

        # Read humidity ADC registers
        self.hRaw = (self.getUInt8(self.HUMID_MSB_0) << 8) | (self.getUInt8(self.HUMID_LSB_0) >> 4)
        
        # Read gas resistance ADC registers
        self.gResRaw = (self.getUInt8(self.GAS_RES_MSB_0) << 2) | self.getUInt8(self.GAS_RES_LSB_0) >> 6           # Shift bits <7:6> right to get LSB for gas resistance

        gasRange = self.getUInt8(self.GAS_RES_LSB_0) & 0x0F

        self.measTime = ticks_ms()  # Capture latest measurement time (ms since Pico powered on)

        # Calculate the compensated reading values from the the raw ADC data
        self.calcTemperature(self.tRaw)
        self.intCalcPressure(self.pRaw)
        self.intCalcHumidity(self.hRaw, self.tRead)
        self.intCalcgRes(self.gResRaw, gasRange)

    # A baseline gas resistance is required for the IAQ calculation - it should be taken in a well ventilated area without obvious air pollutants
    # Take 60 readings over a ~5min period and find the mean
    # Establish the baseline gas resistance reading and the ambient temperature.
    # These values are required for air quality calculations
    # When the baseline process is complete, values for gBase and tAmbient are stored in a file
    # On subsequent power cycles of the board, this function will look for that file and take the baseline values stored there
    # To force the baselines process to be run again, call the function like this: calcBaselines(True)
    def calcBaselines(self, forcedRun=False):
        if (self.bme688InitFlag == False):
            self.bme688Init()
        if (self.gasInit == False):
            self.setupGasSensor()

        self.screen.clear()
        self.screen.displayText("Setting Baseline", 2)
        self.screen.show()
        
        try: # Look for a 'baselines.txt' file existing - if it does, take the baseline values from there (unless 'forcedRun' is set to True)
            if not forcedRun:
                f = open("baselines.txt", "r")
                self.gBase = float(f.readline())
                self.tAmbient = float(f.readline())
            else:
                raise Exception("RUNNING BASELINE PROCESS")
        except: # If there is no file, an exception is raised, and the baseline process will be carried out (creating a new file at the end)
            self.ambTempFlag = False

            burnInReadings = 0
            burnInData = 0
            ambTotal = 0
            progress = 0
            while (burnInReadings < 60):               # Measure data and continue summing gas resistance until 60 readings have been taken
                progress = math.trunc((burnInReadings / 60) * 100)
                self.screen.clear()
                self.screen.displayText(str(progress) + "%", 4, 50)
                self.screen.displayText("Setting Baseline", 2)
                self.screen.show()
                self.measureData()
                burnInData = burnInData + self.gRes
                ambTotal = ambTotal + self.newAmbTemp
                sleep_ms(5000)
                burnInReadings = burnInReadings + 1

            self.gBase = (burnInData / 60)             # Find the mean gas resistance during the period to form the baseline
            self.tAmbient = (ambTotal / 60)            # Calculate the ambient temperature as the mean of the 60 initial readings

            # Save baseline values to a file
            f = open("baselines.txt", "w") #open in write - creates if not existing, will overwrite if it does
            f.write(str(self.gBase) + "\r\n")
            f.write(str(self.tAmbient) + "\r\n")
            f.close()
            
            self.ambTempFlag = True
        
        self.screen.clear()
        self.screen.displayText("Setup Complete!", 2)
        self.screen.show()
        sleep_ms(2000)
        self.screen.clear()
        self.screen.show()

    # Read Temperature from sensor as a Number.
    # Units for temperature are in °C (Celsius) or °F (Fahrenheit) according to selection.
    def readTemperature(self, temperature_unit="C"):
        temperature = self.tRead
        # Change temperature from °C to °F if user selection requires it
        if (temperature_unit == "F"):
            temperature = ((temperature * 18) + 320) / 10

        return temperature

    # Read Pressure from sensor as a Number.
    # Units for pressure are in Pa (Pascals) or mBar (millibar) according to selection.
    def readPressure(self, pressure_unit="Pa"):
        pressure = self.pRead
        #Change pressure from Pascals to millibar if user selection requires it
        if (pressure_unit == "mBar"):
            pressure = pressure / 100

        return pressure

    # Read Humidity from sensor as a Number.
    # Humidity is output as a percentage.
    def readHumidity(self):
        return self.hRead

    # Read Gas Resistance from sensor as a Number.
    # Units for gas resistance are in Ohms.
    def readGasRes(self):
        if (self.gasInit == False):
            self.screen.clear()
            self.screen.displayText("ERROR", 2)
            self.screen.displayText("Setup Gas Sensor", 3)
            self.screen.show()
            return 0
        return self.gRes

    # Read eCO2 from sensor as a Number (250 - 40000+ppm).
    # Units for eCO2 are in ppm (parts per million).
    def readeCO2(self):
        if (self.gasInit == False):
            self.screen.clear()
            self.screen.displayText("ERROR", 2)
            self.screen.displayText("Setup Gas Sensor", 3)
            self.screen.show()
            return 0
        self.calcAirQuality()

        return self.eCO2Value

    # Return the Air Quality rating as a percentage (0% = Bad, 100% = Excellent).
    def getAirQualityPercent(self):
        if (self.gasInit == False):
            self.screen.clear()
            self.screen.displayText("ERROR", 2)
            self.screen.displayText("Setup Gas Sensor", 3)
            self.screen.show()
            return 0
        self.calcAirQuality()

        return self.iaqPercent

    # Return the Air Quality rating as an IAQ score (500 = Bad, 0 = Excellent).
    # These values are based on the BME688 datasheet, Page 11, Table 6.
    def getAirQualityScore(self):
        if (self.gasInit == False):
            self.screen.clear()
            self.screen.displayText("ERROR", 2)
            self.screen.displayText("Setup Gas Sensor", 3)
            self.screen.show()
            return 0
        self.calcAirQuality()

        return self.iaqScore
    
    # Calculate the Index of Air Quality score from the current gas resistance and humidity readings
    # iaqPercent: 0 to 100% - higher value = better air quality
    # iaqScore: 25 should correspond to 'typically good' air, 250 to 'typically polluted' air
    # airQualityRating: Text output based on the iaqScore
    # Calculate the estimated CO2 value (eCO2)
    def calcAirQuality(self):
        humidityScore = 0
        gasScore = 0
        humidityOffset = self.hRead - self.hBase         # Calculate the humidity offset from the baseline setting
        ambTemp = (self.tAmbient / 100)
        temperatureOffset = self.tRead - ambTemp     # Calculate the temperature offset from the ambient temperature
        humidityRatio = ((humidityOffset / self.hBase) + 1)
        temperatureRatio = (temperatureOffset / ambTemp)

        # IAQ Calculations

        if (humidityOffset > 0):                                       # Different paths for calculating the humidity score depending on whether the offset is greater than 0
            humidityScore = (100 - self.hRead) / (100 - self.hBase)
        else:
            humidityScore = self.hRead / self.hBase
            
        humidityScore = humidityScore * self.hWeight * 100

        gasRatio = (self.gRes / self.gBase)

        if ((self.gBase - self.gRes) > 0):                                            # Different paths for calculating the gas score depending on whether the offset is greater than 0
            gasScore = gasRatio * (100 * (1 - self.hWeight))
        else:
            # Make sure that when the gas offset and humidityOffset are 0, iaqPercent is 95% - leaves room for cleaner air to be identified
            gasScore = math.floor(70 + (5 * (gasRatio - 1)))
            if (gasScore > 75):
                gasScore = 75

        self.iaqPercent = math.trunc(humidityScore + gasScore)               # Air quality percentage is the sum of the humidity (25% weighting) and gas (75% weighting) scores
        self.iaqScore = (100 - self.iaqPercent) * 5                               # Final air quality score is in range 0 - 500 (see BME688 datasheet page 11 for details)

        # eCO2 Calculations
        self.eCO2Value = 250 * math.pow(math.e, (0.012 * self.iaqScore))      # Exponential curve equation to calculate the eCO2 from an iaqScore input

        # Adjust eCO2Value for humidity and/or temperature greater than the baseline values
        if (humidityOffset > 0):
            if (temperatureOffset > 0):
                self.eCO2Value = self.eCO2Value * (humidityRatio + temperatureRatio)
            else:
                self.eCO2Value = self.eCO2Value * humidityRatio
        elif (temperatureOffset > 0):
            self.eCO2Value = self.eCO2Value * (temperatureRatio + 1)

        # If measurements are taking place rapidly, breath detection is possible due to the sudden increase in humidity (~7-10%)
        # If this increase happens within a 5s time window, 1200ppm is added to the eCO2 value
        # (These values were based on 'breath-testing' with another eCO2 sensor with algorithms built-in)
        if ((self.measTime - self.measTimePrev) <= 5000):
            if ((self.hRead - self.hPrev) >= 3):
                self.eCO2Value = self.eCO2Value + 1500

        self.eCO2Value = math.trunc(self.eCO2Value)

# The KitronikOLED class enables control of the OLED display screen on the board
# Subclassing FrameBuffer provides support for graphics primitives
# http://docs.micropython.org/en/latest/pyboard/library/framebuf.html
class KitronikOLED(framebuf.FrameBuffer):
    # Write commands to the OLED controller
    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.CHIP_ADDRESS, self.temp)

    # Write data to the OLED controller
    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.CHIP_ADDRESS, self.write_list)

    # Runs on initialisation of the class
    # Sets up all the register definitions and global variables
    def __init__(self, i2cAddr=0x3C, sda=6, scl=7):
        self.CHIP_ADDRESS = i2cAddr    # I2C address as determined by hardware configuration
        # register definitions
        self.SET_CONTRAST = const(0x81)
        self.SET_ENTIRE_ON = const(0xA4)
        self.SET_NORM_INV = const(0xA6)
        self.SET_DISP = const(0xAE)
        self.SET_MEM_ADDR = const(0x20)
        self.SET_COL_ADDR = const(0x21)
        self.SET_PAGE_ADDR = const(0x22)
        self.SET_DISP_START_LINE = const(0x40)
        self.SET_SEG_REMAP = const(0xA0)
        self.SET_MUX_RATIO = const(0xA8)
        self.SET_COM_OUT_DIR = const(0xC0)
        self.SET_DISP_OFFSET = const(0xD3)
        self.SET_COM_PIN_CFG = const(0xDA)
        self.SET_DISP_CLK_DIV = const(0xD5)
        self.SET_PRECHARGE = const(0xD9)
        self.SET_VCOM_DESEL = const(0xDB)
        self.SET_CHARGE_PUMP = const(0x8D)

        sda = Pin(sda)
        scl = Pin(scl)
        self.i2c = I2C(1, sda=sda, scl=scl, freq=100_000, timeout=100_000)

        self.plotArray = []
        self.plotYMin = 0
        self.plotYMax = 100
        self.yPixelMin = 63
        self.yPixelMax = 12

        self.temp = bytearray(2)
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1

        self.width = 128
        self.height = 64
        self.external_vcc = False
        self.pages = 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    # Initialise the display settings and start the display clear
    def init_display(self):
        for cmd in (
            self.SET_DISP | 0x00,  # off
            # address setting
            self.SET_MEM_ADDR,
            0x00,  # horizontal
            # resolution and layout
            self.SET_DISP_START_LINE | 0x00,
            self.SET_SEG_REMAP,# | 0x01,  # Set to either 0xA0 or A1, flips screen horizontally
            self.SET_MUX_RATIO,
            self.height - 1,
            self.SET_COM_OUT_DIR, #| 0x08, # Set to either 0xC0 or 0xC8, flips screen vertically
            self.SET_DISP_OFFSET,
            0x00,
            self.SET_COM_PIN_CFG,
            0x02 if self.width > 2 * self.height else 0x12,
            # timing and driving scheme
            self.SET_DISP_CLK_DIV,
            0x80,
            self.SET_PRECHARGE,
            0x22 if self.external_vcc else 0xF1,
            self.SET_VCOM_DESEL,
            0x30,  # 0.83*Vcc
            # display
            self.SET_CONTRAST,
            0xFF,  # maximum
            self.SET_ENTIRE_ON,  # output follows RAM contents
            self.SET_NORM_INV,  # not inverted
            # charge pump
            self.SET_CHARGE_PUMP,
            0x10 if self.external_vcc else 0x14,
            self.SET_DISP | 0x01,
        ):  # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    # Screen will switch off, but retain the information that was displayed
    def poweroff(self):
        self.write_cmd(self.SET_DISP | 0x00)

    # Turn the screen back on - do not need to re-display what was showing as the information is retained
    def poweron(self):
        self.write_cmd(self.SET_DISP | 0x01)

    # 0 = Dim to 150 = Bright
    def contrast(self, contrast):
        self.write_cmd(self.SET_CONTRAST)
        self.write_cmd(contrast)

    # 0 = White on black, 1 = Black on white
    def invert(self, invert):
        self.write_cmd(self.SET_NORM_INV | (invert & 1))

    # Set text to display on a particular line (1 - 6) and an x-axis offset can be set (0 - 127, 0 is default)
    # If the text is longer than than the screen it will be cut off, it will not be pushed to the next line (16 characters max per line)
    # Need to call 'show()' to make the text actually display
    def displayText(self, text, line, x_offset=0):
        if (line < 1):
            line = 1
        if (line > 6):
            line = 6

        y = (line * 11) - 10

        super().text(text, x_offset, y)

    # Make what has been set to display actually appear on the screen
    # Needs to be called after 'displayText()', 'plot()', clear()', 'drawLine()' & 'drawRect()'
    def show(self):
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32
        self.write_cmd(self.SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(self.SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)

    # Plot a live updating graph of a variable
    # Plot y range is pixels 12 down to 63, leaving room for a title or similar on the first line
    # Need to call 'show()' to make the plot actually display
    def plot(self, variable):
        variable = math.trunc(variable)

        if (variable > self.plotYMax):
            self.plotYMax = variable
        if (variable < self.plotYMin):
            self.plotYMin = variable

        entries = len(self.plotArray)
        if (entries >= 128):
            prevX = 0
            prevY = self.plotArray[127]
            self.plotArray.pop(0)
            self.plotArray.append(variable)
        else:
            self.plotArray.append(variable)
            prevX = len(self.plotArray) - 1
            prevY = self.plotArray[prevX]

        for entry in range(entries):
            x = entry
            y = self.plotArray[entry]
            y = math.trunc(self.yPixelMin - (y * ((self.yPixelMin - self.yPixelMax) / (self.plotYMax - self.plotYMin))))
            if (x == 0):
                super().pixel(x, y, 1)
            else:
                self.drawLine(prevX, prevY, x, y)
            prevX = x 
            prevY = y

    # Wipe all data from the screen
    # Need to call 'show()' to make the clear actually happen
    def clear(self):
        super().fill(0)

    # Clear a specific line on the screen
    def clearLine(self, line):
        yPixel = (line - 1) + ((line * 10) - 10)
        super().fill_rect(0, yPixel, 128, 10, 0)

    # Draw a line on the screen (vertical, horizontal or diagonal), setting start and finish (x, y) coordinates
    # Need to call 'show()' to make the line actually display    
    def drawLine(self, start_x, start_y, end_x, end_y):
        super().line(start_x, start_y, end_x, end_y, 1)

    # Draw rectangles with a top left starting (x, y) coordinate and then a width and height
    # Can be filled (True) or just an outline (False)
    # Need to call 'show()' to make the rectangle actually display
    def drawRect(self, start_x, start_y, width, height, fill=False):
        if (fill == False):
            super().rect(start_x, start_y, width, height, 1)
        elif (fill == True):
            super().fill_rect(start_x, start_y, width, height, 1)

