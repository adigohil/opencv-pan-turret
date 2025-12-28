import time
import serial

PORT = "COM5"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=0.5)
time.sleep(2.0)  # Arduino resets when serial opens

# read READY (optional)
line = ser.readline().decode(errors="ignore").strip()
if line:
    print("Arduino:", line)

for a in [90, 60, 120, 90]:
    ser.write(f"{a}\n".encode())
    time.sleep(0.3)
    reply = ser.readline().decode(errors="ignore").strip()
    print("Reply:", reply)

ser.close()
print("Done.")
