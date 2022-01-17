# UNCOMMENT SECTIONS FOR DIFFERENT STAGES OF TUTORIAL (Block comments are surround by ''' ''')
from PicoAirQuality import KitronikZIPLEDs, KitronikBuzzer, KitronikButton
from machine import Timer
import time

zipleds = KitronikZIPLEDs(3)
buzzer = KitronikBuzzer()
buttons = KitronikButton()
'''
frequency = 1000
red = 255
green = 0
blue = 0
brightUp = False
brightness = 100
colourFade = True
brightnessFade = False
'''
'''
# Buzzer Button IRQs
def ButtonA_IRQHandler(pin):
    global frequency
    frequency += 100
    if (frequency > 3000):
        frequency = 3000
    
def ButtonB_IRQHandler(pin):
    global frequency
    frequency -= 100
    if (frequency < 30):
        frequency = 30
'''
'''
# Debounced Buttons - Buzzer or ZIP LEDs
def checkButtonA(callBackParam):
    global buttonAState
    # For Buzzer
    global frequency
    # For ZIP LEDs
    #global colourFade
    #global brightnessFade
    buttonAState = buttonAState <<1 | buttons.buttonA.value() |0xE000
    buttonAState &=0xFFFF
    if buttonAState == 0xEFFF: #button A has been pressed and passes the debouncing test
        # Buzzer
        frequency += 100
        if (frequency > 3000):
            frequency = 3000
        # ZIP LEDs
        #colourFade = True
        #brightnessFade = False

def checkButtonB(callBackParam):
    global buttonBState
    # For Buzzer
    global frequency
    # For ZIP LEDs
    #global colourFade
    #global brightnessFade
    buttonBState = buttonBState <<1 | buttons.buttonB.value() |0xE000
    buttonBState &=0xFFFF
    if buttonBState == 0xEFFF: #button B has been pressed and passes the debouncing test
        # Buzzer
        frequency -= 100
        if (frequency < 30):
            frequency = 30
        # ZIP LEDs
        #colourFade = False
        #brightnessFade = True
'''
'''
# IRQs
buttons.buttonA.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonA_IRQHandler)
buttons.buttonB.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonB_IRQHandler)
'''
'''
# DEBOUNCE TIMERS
debounceTimerA = Timer()
debounceTimerA.init(period=2, mode=Timer.PERIODIC, callback=checkButtonA)
debounceTimerB = Timer()
debounceTimerB.init(period=2, mode=Timer.PERIODIC, callback=checkButtonB)

buttonAState = 0 
buttonBState = 0
'''

while True:
    # Simple Button Check
    if (buttons.buttonA.value() == True):
        buzzer.playTone_Length(1000, 2000)

    '''
    # Buzzer
    buzzer.playTone(frequency)
    '''
    '''
    # ZIP LEDs
    if colourFade:
        if (red > 0 and blue == 0):
            red -= 1
            green += 1
        if (green > 0 and red == 0):
            green -= 1
            blue += 1
        if (blue > 0 and green == 0):
            red += 1
            blue -= 1
    elif brightnessFade:
        if (brightness == 100):
            brightUp = False
        elif (brightness == 0):
            brightUp = True

        if brightUp:
            brightness = brightness + 1
        elif not(brightUp):
            brightness = brightness - 1

    zipleds.setLED(0, (red, green, blue))
    zipleds.setLED(1, (red, green, blue))
    zipleds.setLED(2, (red, green, blue))
    zipleds.setBrightness(brightness)
    zipleds.show()
    time.sleep_ms(25)
    '''
