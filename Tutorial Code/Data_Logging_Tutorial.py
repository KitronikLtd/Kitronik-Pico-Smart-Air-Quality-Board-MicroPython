from PicoAirQuality import KitronikBME688, KitronikRTC, KitronikDataLogger
import time

bme688 = KitronikBME688()
rtc = KitronikRTC()
log = KitronikDataLogger("data_log.txt", "semicolon")

rtc.setDate(2, 11, 2021)
rtc.setTime(12, 0, 0)

log.writeProjectInfo("User Name", "Subject A")
log.setupDataFields("Date", "Time", "Temperature", "Pressure", "Humidity")

while True:
    bme688.measureData()
    log.storeDataEntry(rtc.readDateString(), rtc.readTimeString(), str(bme688.readTemperature()), str(bme688.readPressure()), str(bme688.readHumidity()))
    time.sleep_ms(1000)