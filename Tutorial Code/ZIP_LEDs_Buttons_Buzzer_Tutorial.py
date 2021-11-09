# UNCOMMENT SECTIONS FOR DIFFERENT STAGES OF TUTORIAL
from PicoAirQuality import KitronikZIPLEDs, KitronikBuzzer, KitronikButton
import time

zipleds = KitronikZIPLEDs(3)
buzzer = KitronikBuzzer()
buttons = KitronikButton()

frequency = 1000
red = 255
green = 0
blue = 0
brightUp = False
brightness = 100
colourFade = True
brightnessFade = False

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

# OR

# ZIP LED Button IRQs
#def ButtonA_IRQHandler(pin):
#    global colourFade
#    global brightnessFade
#    colourFade = True
#    brightnessFade = False
    
#def ButtonB_IRQHandler(pin):
#    global colourFade
#    global brightnessFade
#    colourFade = False
#    brightnessFade = True
    
buttons.buttonA.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonA_IRQHandler)
buttons.buttonB.irq(trigger=machine.Pin.IRQ_RISING, handler=ButtonB_IRQHandler)

while True:
    #if (buttons.buttonA.value() == True):
    #    buzzer.playTone_Length(1000, 2000)
    buzzer.playTone(frequency)
    #if colourFade:
    #    if (red > 0 and blue == 0):
    #        red -= 1
    #        green += 1
    #    if (green > 0 and red == 0):
    #        green -= 1
    #        blue += 1
    #    if (blue > 0 and green == 0):
    #        red += 1
    #        blue -= 1
    #elif brightnessFade:
    #    if (brightness == 100):
    #        brightUp = False
    #    elif (brightness == 0):
    #        brightUp = True

    #    if brightUp:
    #        brightness = brightness + 1
    #    elif not(brightUp):
    #        brightness = brightness - 1

    #zipleds.setLED(0, (red, green, blue))
    #zipleds.setLED(1, (red, green, blue))
    #zipleds.setLED(2, (red, green, blue))
    #zipleds.setBrightness(brightness)
    #zipleds.show()
    #time.sleep_ms(25)

