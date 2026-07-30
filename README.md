# DAM SleepAnalyzer

A lightweight Python tool for quantifying **Drosophila sleep** from activity data collected using the **Drosophila Activity Monitoring (DAM) System**.

The script converts minute-by-minute locomotor activity into binned sleep duration using the standard Drosophila sleep definition:

> **Sleep is defined as at least 5 consecutive minutes of inactivity.**

The output reports total sleep (minutes) within user-defined time bins (30 minutes by default).

---

## Features

- Quantifies sleep from DAM activity data
- Uses the standard 5-minute inactivity criterion
- Supports customizable time-bin durations
- Exports sleep summaries directly to CSV
- Simple, lightweight implementation using only NumPy and pandas

---

## Requirements

- Python 3.8+
- pandas
- numpy

Install dependencies:

```bash
pip install pandas numpy
```

---

## Input Format

The input file should be a CSV exported from the DAM analysis pipeline.

Example:

| Time | Fly1 | Fly2 | Fly3 |
|------|------|------|------|
| 0 | 0 | 1 | 0 |
| 1 | 0 | 0 | 2 |
| 2 | 0 | 0 | 0 |
| ... | ... | ... | ... |

where

- the **first column** contains time points (typically minutes),
- each additional column corresponds to one fly,
- activity values represent locomotor counts,
- missing values are automatically treated as zero.

Example filename:

```
DAM_Data.csv
```

---

## Sleep Definition

For each fly,

- activity ≤ 0 is considered inactivity,
- sleep begins after **5 consecutive minutes** of inactivity,
- all minutes within a qualifying inactivity bout are counted as sleep,
- sleep is summarized within fixed time bins (30 min by default).

The default parameters are

```python
inactivity_threshold = 0
consecutive_periods = 5
bin_duration = 30
```

These values can be modified if desired.

---

## Usage

Edit the input and output filenames:

```python
file_path = "DAM_Data.csv"
output_file = "DAM_sleep_30min_result.csv"
```

Run:

```bash
python sleep_analysis.py
```

---

## Output

The output is a CSV file where

- each column represents one fly,
- each row corresponds to one time bin.

Example:

| Fly_1 | Fly_2 | Fly_3 |
|-------|-------|-------|
| 18 | 22 | 15 |
| 25 | 27 | 19 |
| 16 | 20 | 24 |

Values represent **minutes of sleep within each time bin**.

---

## Customization

### Change the bin duration

For hourly sleep:

```python
analyzer = FlySleepAnalyzer(file_path, bin_duration=60)
```

### Change the inactivity threshold

```python
analyzer.calculate_sleep(
    inactivity_threshold=0,
    consecutive_periods=5
)
```

---

## Algorithm

For each fly, the script

1. Reads activity counts.
2. Detects consecutive inactive periods.
3. Identifies sleep bouts lasting at least 5 minutes.
4. Accumulates sleep duration within each time bin.
5. Exports the results as a CSV table.

---

## Citation

If you use this software in published work, please cite the relevant publications describing the experimental methods or analysis pipeline.
Wu B., He L., Xiao Y., Du J., Wang X., Zhao Z. (2021). Juvenile hormone receptor MET regulates sleep and neuronal morphology via glial-neuronal crosstalk. Journal of Genetics and Genomics. 48(8): 706-715.
https://doi.org/10.1016/j.jgg.2021.04.010.


If you modify or extend this script, please acknowledge the original implementation.

---

## Copyright

Copyright © 2024 Binbin Wu.

This software was originally developed by **Binbin Wu** for analyzing sleep data obtained from the **Drosophila Activity Monitoring (DAM) System**.

---

## License

This repository is released under the MIT License unless otherwise specified.
