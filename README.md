# DAM Sleep Analysis

A Python desktop app that calculates sleep from one-minute Drosophila Activity Monitor (DAM) recordings. Choose an activity CSV, set the bin size and sleep criteria, and export the sleep minutes for each fly.

## Setup

You need Python 3 with Tkinter, plus NumPy and pandas. Open a terminal in the folder containing [`DAM_Sleep_GUI.py`](DAM_Sleep_GUI.py) and run:

```bash
python3 -m pip install numpy pandas
python3 DAM_Sleep_calculation.py
```

If your Python command is `python`, use it for both commands. To check whether your Python installation includes Tkinter, run `python3 -m tkinter`. A small test window should open.

## Input CSV

Save the recording as a comma-separated CSV with a header row and one row per minute. Put time in the first column and each fly’s activity counts in its own column.

```csv
Time(min),Fly_1,Fly_2
0,0,2
1,0,1
2,1,0
3,0,0
4,2,0
5,0,0
```

- Time can start at `0`, `1`, or a later whole minute. It must increase by exactly one each row.
- Give each column a unique name. Use nonnegative numbers for activity counts.
- Keep every row the same width as the header. Blank activity cells are scored as zero, and the app reports how many it found.

## Calculate and export

1. Click **Browse…** and select your activity CSV.
2. Set **Bin size (min)** and **Sleep criteria (inactivity period, min)**. The defaults are 30 minutes per bin and 5 consecutive minutes of inactivity.
3. Click **Calculate sleep** to validate the file and preview the results.
4. Click **Save CSV…** to export all bins.

## Read the results

Each output row represents one bin. `Time(min)` is the bin’s first recorded minute. The remaining columns contain sleep minutes for each fly, numbered `Fly_1`, `Fly_2`, and so on in the input column order.

For the sample above, a **3-minute bin** and a **2-minute sleep criterion** produce:

```csv
Time(min),Fly_1,Fly_2
0,2,0
3,0,3
```

A minute with zero activity is inactive. When an inactivity run reaches the sleep criterion, the app counts every minute in that run. Each bin is scored independently, so an inactivity run spanning a bin boundary is split at that boundary. If the recording ends in a partial bin, an inactivity run still in progress at the end is excluded, following the original script’s scoring.

## Attribution

Original sleep-analysis script by Binbin Wu. If you use this tool for research, cite the relevant work for your sleep-scoring method.
