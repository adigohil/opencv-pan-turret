# opencv-pan-turret

A real-time computer vision tracking project that detects a colored target in a webcam feed, logs tracking data over time, and generates analysis plots and statistics.  
The goal is to understand the full pipeline from vision → measurements → error → control signals before wiring the pan/tilt hardware.

This project is intentionally built in stages: first software-only validation, then hardware integration.

---

## What this project does

- Detects a colored target in real time using OpenCV (HSV thresholding + contour detection)
- Tracks the target position in the image frame (target_x, target_y)
- Computes tracking error relative to the image center (error_x, error_y)
- Converts pixel error into an approximate angular offset (degrees)
- Logs every frame to a CSV file for offline analysis
- Generates plots and statistical metrics from the tracking log

---

## Key outputs

From a single tracking run, the system produces:

- Time-series plots:
  - Target X / Y vs time (px)
  - Error X / Y vs time (px)
  - Angle X vs time (deg)
  - Contour area vs time (px²)
  - Rolling RMS error vs time
- Distributions:
  - Error distribution (px)
  - Angle distribution (deg)
- Summary statistics:
  - Detection rate (%)
  - Mean absolute error (px)
  - RMSE error (px)
  - p90 / p95 error (px)
  - Mean and RMSE angle (deg)
  - Mean contour area (px²)

These metrics are used to evaluate tracking stability and accuracy before closing the control loop with hardware.

---

## Repository structure

```text
opencv-pan-turret/
├─ python/
│  ├─ main.py            # Live OpenCV tracker + CSV logger
│  ├─ plot_log.py        # Log analysis, plots, and statistics
│  ├─ servo_serial.py    # Serial interface (Arduino, future use)
│  └─ servo_test.py      # Servo test utilities
│
├─ logs/
│  └─ tracking_log_*.csv # Example tracking logs
│
├─ arduino/
│  └─ (future servo control sketches)
│
├─ .gitignore
├─ README.md
└─ LICENSE

## Requirements

- Python 3.10+ (tested with Python 3.13)
- OpenCV
- NumPy
- Pandas
- Matplotlib

## Setup

From the repository root:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

## Running the tracker

To start the live OpenCV tracker, run:

```bash
python python/main.py
This will:
- Open the webcam feed
- Detect and track a colored target in real time
- Draw tracking overlays on the video stream
- Log tracking data to a CSV file inside the `logs/` directory

Press `q` to exit cleanly and finalize the log file.

## Analyzing tracking logs

After a tracking session, analyze the most recent log with:

```bash
python python/plot_log.py

## Notes

Some values like `center_x`, `center_y`, and `min_area_setting` appear as flat lines in plots because they are constants during a run (camera resolution and settings don’t change frame-to-frame). The more important plots for performance are `error_x/error_y`, `angle_x/angle_y`, and the rolling RMS error.

## Future work

- Send angle/servo commands over serial to an Arduino
- Add a simple control loop (P-controller, then PID)
- Calibrate pixel-to-angle mapping for better accuracy
- Improve robustness for lighting changes and background clutter
- Measure tracking latency and servo response

## License

MIT
