import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def pick_time_axis(df: pd.DataFrame):
    # Prefer timestamp_iso if present
    if "timestamp_iso" in df.columns:
        ts = pd.to_datetime(df["timestamp_iso"], errors="coerce")
        if ts.notna().any():
            t = (ts - ts.iloc[0]).dt.total_seconds()
            return t, "time (s)"
    # fallback to index
    return df.index.astype(float), "index"


def plot_series(df: pd.DataFrame, x, xlabel: str, col: str, title: str, save_path: Path | None):
    y = df[col]
    # If column has blanks, pandas may treat as object -> coerce to numeric
    y = pd.to_numeric(y, errors="coerce")

    plt.figure()
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(col)
    plt.title(title)
    plt.grid(True)

    if save_path is not None:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=None,
        help="Path to a tracking_log_*.csv file (default: latest in logs folder)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save plots as PNGs into /plots instead of only showing them",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not show plot windows (useful with --save)",
    )
    args = parser.parse_args()

    logs_dir = Path("logs")
    if args.csv_path:
        path = Path(args.csv_path)
    else:
        # Pick newest tracking_log_*.csv
        candidates = sorted(logs_dir.glob("tracking_log_*.csv"),
                            key=lambda p: p.stat().st_mtime)
        if not candidates:
            print("No logs found in /logs. Run main.py and record a log first.")
            return
        path = candidates[-1]

    if not path.exists():
        print(f"Log file not found: {path}")
        return

    df = pd.read_csv(path)
    t, xlabel = pick_time_axis(df)

    # Columns your logger actually writes
    preferred = [
        ("error_x_px", "Error X (pixels)"),
        ("angle_x_deg", "Angle X (deg)"),
        ("contour_area_px", "Contour area (px)"),
        ("target_found", "Target found (0/1)"),
    ]

    # Optional extras if present
    extras = ["target_x", "center_x", "target_y",
              "center_y", "min_area_setting"]

    plots_dir = None
    if args.save:
        plots_dir = Path("plots")
        plots_dir.mkdir(exist_ok=True)

    found_any = False

    for col, nice in preferred:
        if col in df.columns:
            found_any = True
            save_path = None
            if plots_dir is not None:
                save_path = plots_dir / f"{path.stem}_{col}.png"
            plot_series(df, t, xlabel, col,
                        f"{nice} vs time ({path.name})", save_path)

    for col in extras:
        if col in df.columns:
            found_any = True
            save_path = None
            if plots_dir is not None:
                save_path = plots_dir / f"{path.stem}_{col}.png"
            plot_series(df, t, xlabel, col,
                        f"{col} vs time ({path.name})", save_path)

    if not found_any:
        print("No plottable columns found.")
        print("Found columns:", list(df.columns))
        return

    if plots_dir is not None:
        print(f"Saved plots to: {plots_dir.resolve()}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
