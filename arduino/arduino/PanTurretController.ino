#include <Servo.h>

Servo servo;
int angle = 90;
String buf = "";

void setup() {
  Serial.begin(115200);
  servo.attach(9);
  servo.write(angle);
  delay(200);
  Serial.println("READY");
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      buf.trim();
      if (buf.length() > 0) {
        int val = buf.toInt();
        if (val >= 0 && val <= 180) {
          angle = val;
          servo.write(angle);
          Serial.print("OK ");
          Serial.println(angle);
        } else {
          Serial.println("ERR range");
        }
      }
      buf = "";
    } else {
      buf += c;
      if (buf.length() > 16) buf = "";
    }
  }
}
