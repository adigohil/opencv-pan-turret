import cv2
import numpy as np

# ----------------------------
# Config
# ----------------------------
WINDOW_MAIN = "Camera Test"
WINDOW_MASK = "Mask"
WINDOW_TUNE = "HSV Tuning"

CAM_INDEX = 0

# Approx camera field-of-view (horizontal only for pan)
FOV_X_DEG = 60.0

# Default HSV range to catch yellow-green / lime / green
# Hue in OpenCV is 0-179
DEFAULTS = {
    "H Min": 20,
    "H Max": 95,
    "S Min": 50,
    "S Max": 255,
    "V Min": 40,
    "V Max": 255,
}

# Text + drawing colors (OpenCV uses BGR)
COLOR_TEXT = (255, 0, 255)     # purple
COLOR_OK = (255, 0, 0)         # blue
COLOR_BAD = (0, 0, 255)        # red
COLOR_CROSS = (255, 255, 255)  # white crosshair
COLOR_TARGET = (0, 255, 255)   # yellow marker for detected target

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

    # Optional: minimum area to accept a blob (filters noise)
    cv2.createTrackbar("Min Area", WINDOW_TUNE, 1200, 30000, nothing)


def get_hsv_from_trackbars():
    hmin = cv2.getTrackbarPos("H Min", WINDOW_TUNE)
    hmax = cv2.getTrackbarPos("H Max", WINDOW_TUNE)
    smin = cv2.getTrackbarPos("S Min", WINDOW_TUNE)
    smax = cv2.getTrackbarPos("S Max", WINDOW_TUNE)
    vmin = cv2.getTrackbarPos("V Min", WINDOW_TUNE)
    vmax = cv2.getTrackbarPos("V Max", WINDOW_TUNE)
    min_area = cv2.getTrackbarPos("Min Area", WINDOW_TUNE)

    # Ensure mins <= maxes
    hmin, hmax = min(hmin, hmax), max(hmin, hmax)
    smin, smax = min(smin, smax), max(smin, smax)
    vmin, vmax = min(vmin, vmax), max(vmin, vmax)

    lower = np.array([hmin, smin, vmin], dtype=np.uint8)
    upper = np.array([hmax, smax, vmax], dtype=np.uint8)

    return lower, upper, min_area


def draw_crosshair(frame, cx, cy):
    # Make it thicker so it stands out
    cv2.line(frame, (cx - 40, cy), (cx + 40, cy), COLOR_CROSS, 3)
    cv2.line(frame, (cx, cy - 40), (cx, cy + 40), COLOR_CROSS, 3)
    cv2.circle(frame, (cx, cy), 5, COLOR_CROSS, -1)


def put_label(frame, text, x, y, color, scale=0.8, thickness=2):
    cv2.putText(frame, text, (x, y), FONT, scale,
                color, thickness, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    # Optional: set resolution (comment out if you want default)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("Camera opened successfully")

    cv2.namedWindow(WINDOW_MAIN, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_MASK, cv2.WINDOW_NORMAL)
    create_trackbars()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("ERROR: Failed to read frame.")
            break

        # Mirror the view so movement feels natural
        frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        # 1) Convert to HSV and threshold
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower, upper, min_area = get_hsv_from_trackbars()
        mask = cv2.inRange(hsv, lower, upper)

        # 2) Clean up mask (reduces speckles, improves contour stability)
        mask = cv2.GaussianBlur(mask, (7, 7), 0)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        # 3) Find target (largest contour)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        target_found = False
        tx = 0

        if contours:
            best = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(best)

            if area >= max(50, min_area):
                M = cv2.moments(best)
                if M["m00"] != 0:
                    tx = int(M["m10"] / M["m00"])
                    ty = int(M["m01"] / M["m00"])
                    target_found = True

                    # Draw contour + target marker
                    cv2.drawContours(frame, [best], -1, COLOR_TARGET, 2)
                    cv2.circle(frame, (tx, ty), 8, COLOR_TARGET, -1)

        # 4) Crosshair at center of frame
        draw_crosshair(frame, cx, cy)

        # 5) Compute PAN-only error + angle (X-axis only)
        if target_found:
            err_x = tx - cx

            # Convert pixel error to angular error using horizontal FOV
            ang_x = (err_x / w) * FOV_X_DEG

            put_label(frame, "Target: FOUND", 20, 45,
                      COLOR_OK, scale=1.2, thickness=3)
            put_label(frame, f"Error px:  X={err_x:+d}", 20, 85, COLOR_TEXT)
            put_label(frame, f"Angle deg: X={ang_x:+.2f}", 20, 120, COLOR_TEXT)
        else:
            put_label(frame, "Target: NOT FOUND", 20, 45,
                      COLOR_BAD, scale=1.2, thickness=3)
            put_label(frame, "Error px:  X=  0", 20, 85, COLOR_TEXT)
            put_label(frame, "Angle deg: X=+0.00", 20, 120, COLOR_TEXT)

        # 6) Show windows
        cv2.imshow(WINDOW_MAIN, frame)
        cv2.imshow(WINDOW_MASK, mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:  # q or ESC
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
