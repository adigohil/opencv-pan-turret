import time
import serial


class ServoSerial:
    def __init__(self, port="COM5", baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.05)
        time.sleep(2.0)  # Arduino resets on open
        self.last_sent = None
        self.last_time = 0.0

    def send(self, angle, min_interval=0.05, min_step=1):
        angle = int(max(0, min(180, angle)))
        now = time.time()

        if self.last_sent is not None and abs(angle - self.last_sent) < min_step:
            return
        if (now - self.last_time) < min_interval:
            return

        self.ser.write(f"{angle}\n".encode())
        self.last_sent = angle
        self.last_time = now

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass
