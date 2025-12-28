import argparse
from pathlib import Path

import numpy as pd
import pandas as pd
import matplotlib.pyplot as plt


# ----------------------------
# Helpers
# ----------------------------
def pick_time_axis(df: pd.DataFrame):
    if "timestamp_iso" in df.columns:
        ts = pd.to_datetime(df["timestamp_iso"], errors="coerce")
        if ts.notna().any():
            t = (ts - ts.iloc[0]).dt.total_seconds()
            return t, "Time (s)"
    return df.index.astype(float), "Index"


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return to_num(df[col])


def pct(x: float) -> float:
    return 100.0 * x


def rmse(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) == 0:
        return float("nan")
    return float((x.pow(2).mean()) ** 0.5)


def mae(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) == 0:
        return float("nan")
    return float(x.abs().mean())


def pctl(x: pd.Series, q: float) -> float:
    x = x.dropna()
    if len(x) == 0:
        return float("nan")
    return float(x.quantile(q))


def rolling_rms(x: pd.Series, window: int) -> pd.Series:
    # rolling RMS of x
    return (x.pow(2).rolling(window=window, min_periods=max(1, window // 3)).mean()) ** 0.5


def plot_line(x, y, xlabel, ylabel, title, save_path=None):
    mask = x.notna() & y.notna()
    x2 = x[mask]
    y2 = y[mask]
    if len(x2) == 0:
        return False

    plt.figure(figsize=(12, 5))
    plt.plot(x2, y2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path is not None:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
    return True


def plot_step(x, y, xlabel, ylabel, title, save_path=None):
    mask = x.notna() & y.notna()
    x2 = x[mask]
    y2 = y[mask]
    if len(x2) == 0:
        return False

    plt.figure(figsize=(12, 4))
    plt.step(x2, y2, where="post")
    plt.ylim(-0.1, 1.1)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path is not None:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
    return True


def plot_hist(y, title, xlabel, save_path=None, bins=50):
    y2 = y.dropna()
    if len(y2) == 0:
        return False

    plt.figure(figsize=(10, 5))
    plt.hist(y2, bins=bins)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Count")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path is not None:
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
    return True


def print_stats_report(df: pd.DataFrame, t: pd.Series, log_name: str):
    tf = safe_series(df, "target_found").fillna(0).astype(int)

    err_px = safe_series(df, "error_x_px")
    ang_deg = safe_series(df, "angle_x_deg")
    area = safe_series(df, "contour_area_px")

    # Only evaluate error when target is found
    found_mask = tf == 1
    err_found = err_px.where(found_mask)
    ang_found = ang_deg.where(found_mask)
    area_found = area.where(found_mask)

    # Time info
    duration = float("nan")
    if len(t) > 0 and t.notna().any():
        duration = float(t.dropna().iloc[-1])

    total = len(df)
    found = int(tf.sum())
    found_rate = (found / total) if total > 0 else float("nan")

    # "Stability / accuracy" style metrics (relative to frame center)
    report = {
        "Log": log_name,
        "Rows": total,
        "Duration (s)": duration,
        "Detection rate (%)": pct(found_rate) if total > 0 else float("nan"),
        "Mean abs error |px| (found only)": mae(err_found),
        "RMSE error px (found only)": rmse(err_found),
        "p90 abs error px (found only)": pctl(err_found.abs(), 0.90),
        "p95 abs error px (found only)": pctl(err_found.abs(), 0.95),
        "Mean abs angle |deg| (found only)": mae(ang_found),
        "RMSE angle deg (found only)": rmse(ang_found),
        "p95 abs angle deg (found only)": pctl(ang_found.abs(), 0.95),
        "Mean contour area px (found only)": float(area_found.dropna().mean()) if area_found.notna().any() else float("nan"),
    }

    # "Jitter" metric: frame-to-frame change in error (lower is smoother)
    d_err = err_found.diff()
    report["Mean |Δerror| px/frame (found only)"] = mae(d_err)
    report["p95 |Δerror| px/frame (found only)"] = pctl(d_err.abs(), 0.95)

    # Print nicely
    print("\n================= Tracking Stats =================")
    for k, v in report.items():
        if isinstance(v, float):
            if v != v:  # NaN
                print(f"{k}: N/A")
            else:
                if "rate" in k.lower() or "(%)" in k:
                    print(f"{k}: {v:.2f}")
                else:
                    print(f"{k}: {v:.3f}")
        else:
            print(f"{k}: {v}")
    print("==================================================\n")


# ----------------------------
# Main
# ----------------------------
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
    parser.add_argument(
        "--window",
        type=float,
        default=0.5,
        help="Rolling window (seconds) for smoothing metrics (default: 0.5s)",
    )
    args = parser.parse_args()

    logs_dir = Path("logs")

    if args.csv_path:
        path = Path(args.csv_path)
    else:
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

    # Stats report (this is the main new value)
    print_stats_report(df, t, path.name)

    # Determine dt + rolling window in frames (if time axis is real)
    # Fallback to ~30 FPS if we can’t estimate
    dt_est = None
    if xlabel == "Time (s)":
        t2 = t.dropna()
        if len(t2) >= 2:
            diffs = t2.diff().dropna()
            if len(diffs) > 0:
                dt_est = float(diffs.median())
    fps_est = 30.0 if (dt_est is None or dt_est <= 0) else (1.0 / dt_est)
    win_frames = max(3, int(args.window * fps_est))

    tf = safe_series(df, "target_found").fillna(0).astype(int)

    err_px = safe_series(df, "error_x_px")
    ang_deg = safe_series(df, "angle_x_deg")
    area_px = safe_series(df, "contour_area_px")

    # Only "found" values for some plots
    err_found = err_px.where(tf == 1)
    ang_found = ang_deg.where(tf == 1)

    plots_dir = None
    if args.save:
        plots_dir = Path("plots")
        plots_dir.mkdir(exist_ok=True)

    def sp(name: str) -> Path | None:
        if plots_dir is None:
            return None
        return plots_dir / f"{path.stem}_{name}.png"

    found_any = False

    # Core plots with units
    found_any |= plot_line(
        t, err_found,
        xlabel,
        "Error X (px)",
        f"Error X vs {xlabel} ({path.name})",
        save_path=sp("error_x_px"),
    )

    found_any |= plot_line(
        t, ang_found,
        xlabel,
        "Angle X (deg)",
        f"Angle X vs {xlabel} ({path.name})",
        save_path=sp("angle_x_deg"),
    )

    found_any |= plot_line(
        t, area_px.where(tf == 1),
        xlabel,
        "Contour Area (px^2)",
        f"Contour Area vs {xlabel} ({path.name})",
        save_path=sp("contour_area_px"),
    )

    found_any |= plot_step(
        t, tf,
        xlabel,
        "Target Found",
        f"Target Found vs {xlabel} ({path.name})",
        save_path=sp("target_found"),
    )

    # Rolling RMS of error (good “stability” indicator)
    rrms = rolling_rms(err_found, window=win_frames)
    found_any |= plot_line(
        t, rrms,
        xlabel,
        "Rolling RMS Error (px)",
        f"Rolling RMS Error (window ~{args.window:.2f}s) ({path.name})",
        save_path=sp("rolling_rms_error_px"),
    )

    # Histograms (distribution = how noisy it is)
    found_any |= plot_hist(
        err_found,
        f"Error X Distribution (found only) ({path.name})",
        "Error X (px)",
        save_path=sp("error_x_hist"),
        bins=50,
    )

    found_any |= plot_hist(
        ang_found,
        f"Angle X Distribution (found only) ({path.name})",
        "Angle X (deg)",
        save_path=sp("angle_x_hist"),
        bins=50,
    )

    # Optional extras if present
    for col, ylabel in [
        ("target_x", "Target X (px)"),
        ("center_x", "Center X (px)"),
        ("target_y", "Target Y (px)"),
        ("center_y", "Center Y (px)"),
        ("min_area_setting", "Min Area (px^2)"),
    ]:
        if col in df.columns:
            y = to_num(df[col])
            found_any |= plot_line(
                t, y,
                xlabel,
                ylabel,
                f"{col} vs {xlabel} ({path.name})",
                save_path=sp(col),
            )

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
