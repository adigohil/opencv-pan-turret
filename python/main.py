import cv2
import numpy as np
import os
import csv
import shutil
import time
from pathlib import Path
from datetime import datetime

from servo_serial import ServoSerial  # <-- NEW

# ----------------------------
# Config
# ----------------------------
WINDOW_MAIN = "Camera Test"
WINDOW_MASK = "Mask"
WINDOW_TUNE = "HSV Tuning"

CAM_INDEX = 0

# Approx camera field-of-view (horizontal only for pan)
FOV_X_DEG = 60.0

# ----------------------------
# Servo control config (NEW)
# ----------------------------
SERVO_PORT = "COM5"
SERVO_BAUD = 115200

SERVO_CENTER = 90
SERVO_MIN = 10
SERVO_MAX = 170

GAIN = 1.2          # lower = softer, higher = more aggressive
DEADBAND_DEG = 1.0  # ignore small error to avoid jitter
ALPHA = 0.25        # smoothing (0..1)
SEND_HZ = 20        # limit serial writes
MIN_STEP = 1        # ignore tiny angle changes

# Default HSV range to catch yellow-green / lime / green
DEFAULTS = {
    "H Min": 20,
    "H Max": 95,
    "S Min": 50,
    "S Max": 255,
    "V Min": 40,
    "V Max": 255,
}

# Colors (BGR)
COLOR_TEXT = (255, 0, 255)     # purple
COLOR_OK = (255, 0, 0)         # blue
COLOR_BAD = (0, 0, 255)        # red
COLOR_CROSS = (255, 255, 255)  # white crosshair
COLOR_TARGET = (0, 255, 255)   # yellow marker

FONT = cv2.FONT_HERSHEY_SIMPLEX


def nothing(_):
    pass


def create_trackbars():
    cv2.namedWindow(WINDOW_TUNE, cv2.WINDOW_NORMAL)

    cv2.createTrackbar("H Min", WINDOW_TUNE, DEFAULTS["H Min"], 179, nothing)
    cv2.createTrackbar("H Max", WINDOW_TUNE, DEFAULTS["H Max"], 179, nothing)
    cv2.createTrackbar("S Min", WINDOW_TUNE, DEFAULTS["S Min"], 255, nothing)
    cv2.createTrackbar("S Max", WINDOW_TUNE, DEFAULTS["S Max"], 255, nothing)
    cv2.createTrackbar("V Min", WINDOW_TUNE, DEFAULTS["V Min"], 255, nothing)
    cv2.createTrackbar("V Max", WINDOW_TUNE, DEFAULTS["V Max"], 255, nothing)

    cv2.createTrackbar("Min Area", WINDOW_TUNE, 1200, 30000, nothing)


def get_hsv_from_trackbars():
    hmin = cv2.getTrackbarPos("H Min", WINDOW_TUNE)
    hmax = cv2.getTrackbarPos("H Max", WINDOW_TUNE)
    smin = cv2.getTrackbarPos("S Min", WINDOW_TUNE)
    smax = cv2.getTrackbarPos("S Max", WINDOW_TUNE)
    vmin = cv2.getTrackbarPos("V Min", WINDOW_TUNE)
    vmax = cv2.getTrackbarPos("V Max", WINDOW_TUNE)
    min_area = cv2.getTrackbarPos("Min Area", WINDOW_TUNE)

    hmin, hmax = min(hmin, hmax), max(hmin, hmax)
    smin, smax = min(smin, smax), max(smin, smax)
    vmin, vmax = min(vmin, vmax), max(vmin, vmax)

    lower = np.array([hmin, smin, vmin], dtype=np.uint8)
    upper = np.array([hmax, smax, vmax], dtype=np.uint8)
    return lower, upper, min_area, (hmin, hmax, smin, smax, vmin, vmax)


def draw_crosshair(frame, cx, cy):
    cv2.line(frame, (cx - 40, cy), (cx + 40, cy), COLOR_CROSS, 3)
    cv2.line(frame, (cx, cy - 40), (cx, cy + 40), COLOR_CROSS, 3)
    cv2.circle(frame, (cx, cy), 5, COLOR_CROSS, -1)


def put_label(frame, text, x, y, color, scale=0.8, thickness=2):
    cv2.putText(frame, text, (x, y), FONT, scale,
                color, thickness, cv2.LINE_AA)


def create_log_file():
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = logs_dir / f"tracking_log_{ts}.csv"

    f = open(path, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)

    writer.writerow([
        "timestamp_iso",
        "frame_w",
        "frame_h",
        "target_found",
        "target_x",
        "target_y",
        "center_x",
        "center_y",
        "error_x_px",
        "angle_x_deg",
        "contour_area_px",
        "h_min",
        "h_max",
        "s_min",
        "s_max",
        "v_min",
        "v_max",
        "min_area_setting",
    ])

    return path, f, writer


def finalize_log(log_path, log_file):
    """
    Close the file and update logs/tracking_log_latest.csv to point to the most recent run.
    """
    try:
        if log_file is not None:
            log_file.flush()
            os.fsync(log_file.fileno())
            log_file.close()
    except Exception:
        try:
            if log_file is not None:
                log_file.close()
        except Exception:
            pass

    if log_path is not None:
        latest_path = Path("logs") / "tracking_log_latest.csv"
        try:
            shutil.copyfile(str(log_path), str(latest_path))
            print(f"Log saved: {log_path}")
            print(f"Latest log updated: {latest_path}")
        except Exception as e:
            print(f"Log saved: {log_path}")
            print(f"Could not update latest log: {e}")


def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("Camera opened successfully")
    print("Press r to start/stop logging (each ON creates a NEW file)")
    print("Press q to quit")

    cv2.namedWindow(WINDOW_MAIN, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_MASK, cv2.WINDOW_NORMAL)
    create_trackbars()

    # ----------------------------
    # Servo setup (NEW)
    # ----------------------------
    servo = ServoSerial(port=SERVO_PORT, baud=SERVO_BAUD)
    servo_angle = float(SERVO_CENTER)
    servo_smoothed = float(SERVO_CENTER)
    send_interval = 1.0 / SEND_HZ

    logging_on = False
    log_path = None
    log_file = None
    log_writer = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("ERROR: Failed to read frame.")
                break

            frame = cv2.flip(frame, 1)

            h, w = frame.shape[:2]
            cx, cy = w // 2, h // 2

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower, upper, min_area, hsv_vals = get_hsv_from_trackbars()
            hmin, hmax, smin, smax, vmin, vmax = hsv_vals

            mask = cv2.inRange(hsv, lower, upper)

            mask = cv2.GaussianBlur(mask, (7, 7), 0)
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(
                mask, cv2.MORPH_CLOSE, kernel, iterations=2)

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            target_found = False
            tx = 0
            ty = 0
            area_px = 0.0
            err_x = 0
            ang_x = 0.0

            if contours:
                best = max(contours, key=cv2.contourArea)
                area_px = float(cv2.contourArea(best))

                if area_px >= max(50, min_area):
                    M = cv2.moments(best)
                    if M["m00"] != 0:
                        tx = int(M["m10"] / M["m00"])
                        ty = int(M["m01"] / M["m00"])
                        target_found = True

                        cv2.drawContours(frame, [best], -1, COLOR_TARGET, 2)
                        cv2.circle(frame, (tx, ty), 8, COLOR_TARGET, -1)

                        err_x = tx - cx
                        ang_x = (err_x / w) * FOV_X_DEG

            # ----------------------------
            # Servo control (NEW)
            # ----------------------------
            if target_found:
                if abs(ang_x) > DEADBAND_DEG:
                    # If it moves the wrong direction, flip the sign (+ instead of -)
                    servo_angle = servo_angle - (GAIN * ang_x)

                servo_angle = max(SERVO_MIN, min(SERVO_MAX, servo_angle))
                servo_smoothed = (1 - ALPHA) * \
                    servo_smoothed + ALPHA * servo_angle

                servo.send(
                    int(round(servo_smoothed)),
                    min_interval=send_interval,
                    min_step=MIN_STEP
                )

            draw_crosshair(frame, cx, cy)

            if target_found:
                put_label(frame, "Target: FOUND", 20, 45,
                          COLOR_OK, scale=1.2, thickness=3)
                put_label(
                    frame, f"Error px:  X={err_x:+d}", 20, 85, COLOR_TEXT)
                put_label(
                    frame, f"Angle deg: X={ang_x:+.2f}", 20, 120, COLOR_TEXT)
            else:
                put_label(frame, "Target: NOT FOUND", 20, 45,
                          COLOR_BAD, scale=1.2, thickness=3)
                put_label(frame, "Error px:  X=  0", 20, 85, COLOR_TEXT)
                put_label(frame, "Angle deg: X=+0.00", 20, 120, COLOR_TEXT)

            put_label(frame, f"Logging: {'ON' if logging_on else 'OFF'}",
                      20, 155, COLOR_TEXT)

            # Write row while logging is ON
            if logging_on and log_writer is not None:
                ts_iso = datetime.now().isoformat(timespec="milliseconds")
                log_writer.writerow([
                    ts_iso,
                    w,
                    h,
                    1 if target_found else 0,
                    tx if target_found else "",
                    ty if target_found else "",
                    cx,
                    cy,
                    err_x if target_found else "",
                    f"{ang_x:.6f}" if target_found else "",
                    f"{area_px:.2f}" if target_found else "",
                    hmin, hmax, smin, smax, vmin, vmax,
                    min_area,
                ])

            cv2.imshow(WINDOW_MAIN, frame)
            cv2.imshow(WINDOW_MASK, mask)

            key = cv2.waitKey(1) & 0xFF

            # Quit
            if key == ord("q") or key == 27:
                break

            # Toggle logging
            if key == ord("r"):
                if not logging_on:
                    if log_file is not None:
                        finalize_log(log_path, log_file)

                    log_path, log_file, log_writer = create_log_file()
                    logging_on = True
                    print(f"Logging started: {log_path}")
                else:
                    logging_on = False
                    finalize_log(log_path, log_file)
                    log_path = None
                    log_file = None
                    log_writer = None
                    print("Logging paused")

    finally:
        cap.release()
        cv2.destroyAllWindows()

        # Close serial
        servo.close()

        # If user quits while logging is still ON, finalize it too
        if log_file is not None:
            finalize_log(log_path, log_file)


if __name__ == "__main__":
    main()
