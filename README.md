# Vision Guided Pan-Tilt Tracking System

Tracking a moving target looks straightforward until you try to turn pixel motion into stable control signals.

This project builds and validates a real-time computer vision tracking pipeline using OpenCV, with a focus on quantifying error, stability, and signal quality before introducing physical pan/tilt hardware. The goal is not just detection, but understanding how vision noise propagates into measurements and control commands in an embedded system.

---

## What this project does

The pipeline processes a live webcam feed and produces control-ready signals:

- Detects a colored target using HSV thresholding and contour detection

- Tracks target position in the image frame (target_x, target_y)

- Computes pixel error relative to the image center (error_x, error_y)

- Converts pixel error into approximate angular offsets (degrees)

- Logs per-frame tracking data to CSV

- Generates plots and statistical metrics for offline analysis


---

## Why this project matters

Before driving motors, you need to answer:

- How noisy is the vision signal?

- How large are worst-case errors?

- How smooth is the control input frame-to-frame?

- Is detection stable enough for closed-loop control?

---

## Sample results

Below are representative outputs from a single tracking run.

Error and angle signals:


<img width="2403" height="1117" alt="Screenshot 2025-12-28 180256" src="https://github.com/user-attachments/assets/be90a365-525e-44e5-8614-e9e51955f2f2" />

<img width="2381" height="1109" alt="Screenshot 2025-12-28 180242" src="https://github.com/user-attachments/assets/9508e703-4c66-4cae-89c9-a284455d61f8" />

- Error X vs time shows bounded oscillations as the target moves across the frame.

- Angle X vs time demonstrates a smooth control-ready signal without abrupt jumps.


Contour stability:

<img width="2390" height="1113" alt="Screenshot 2025-12-28 180219" src="https://github.com/user-attachments/assets/9b58d030-cae6-4c82-9ddc-46a1b2344822" />


- Contour area remains stable across frames, indicating consistent detection rather than noise spikes or false positives.

---

## Tracking performance summary

Representative run statistics:

- Frames processed: 437

- Duration: 14.55 s

- Detection rate: 100%

Pixel error (found frames only)

- Mean absolute error: 214.3 px

- RMSE error: 237.8 px

- p90 absolute error: 329.0 px

- p95 absolute error: 367.8 px

Angular error

- Mean absolute angle: 10.0°

- RMSE angle: 11.1°

- p95 absolute angle: 17.2°

Signal smoothness

- Mean contour area: 32,378 px²

- Mean |Δerror| per frame: 15.4 px

- p95 |Δerror| per frame: 61.3 px

These metrics indicate a stable, continuous signal suitable for proportional or PID control once hardware is added.

<img width="1057" height="651" alt="Screenshot 2025-12-28 180318" src="https://github.com/user-attachments/assets/7b9e6cf7-e289-4d99-a8bc-4b4522b68125" />

---

## What the results tell us

- 100% detection rate confirms robust segmentation under tested conditions

- Error and angle distributions define the noise envelope a controller must handle

- p95 angular error remains well within typical servo limits

- Low frame-to-frame error change suggests minimal jitter in control input

---

## Repository Structure

opencv-pan-tilt-tracking/
├─ python/
│  ├─ main.py            # Live OpenCV tracker + CSV logger
│  ├─ plot_log.py        # Log analysis, plots, and statistics
│  ├─ servo_serial.py    # Serial interface (Arduino, future use)
│  └─ servo_test.py      # Servo test utilities
│
├─ logs/
│  └─ tracking_log_*.csv # Example tracking logs
│
├─ docs/
│  └─ figures/           # README plots and screenshots
│
├─ arduino/
│  └─ (future servo control sketches)
│
├─ .gitignore
├─ README.md
└─ LICENSE

---

## Requirements

- Python 3.10+ (tested with Python 3.13)

- OpenCV

- NumPy

- Pandas

- Matplotlib

---

## Setup

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

---

## Running the tracker

Clicking the run button will:

- Open the webcam feed

- Track a colored target in real time (green/lime green object)

- Display overlays (centroid, error vectors)

- Log tracking data to logs/tracking_log_*.csv (Press R to begin and R to End)

- Press q to exit cleanly

---

## Running the tracker

Go to plot_log.py and run the program

- Will print the plots and statsical summaries to the console, and will run matplotlib.


----

## Limitations

- Pixel-to-angle conversion is approximate and not camera-calibrated

- Servo dynamics, backlash, and latency are not yet modeled

- Lighting and background complexity were controlled

- End-to-end latency is not yet measured

---

## Future work

- Send angular commands to Arduino over serial

- Implement P and PID controllers

- Camera calibration for accurate angle mapping

- Robust tracking under lighting and clutter changes

- Measure full vision → control → actuation latency


---

## Liscences

MIT


