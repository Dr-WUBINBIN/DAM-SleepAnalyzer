# Binbin Wu complete this sleep_analysis script on 6/30/2024.
# Binbin Wu have this script copyright.
# Please cite related papers if you are using this script or revised script to analyze sleep.

"""Calculate sleep from one-minute DAM activity CSVs.

Run this file to open the desktop app, or import FlySleepAnalyzer for scripts.
"""

import csv
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd

TIME_COLUMN = "Time(min)"


def _read_validated_csv(file_path):
    """Check the layout expected by the desktop app before loading activity values."""
    with open(file_path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        try:
            headers = [header.strip() for header in next(reader, [])]
            if len(headers) < 2:
                raise ValueError("Use a comma-separated header with a time column and at least one fly column.")
            if not all(headers):
                raise ValueError("Row 1 needs a time header and a name for every fly column.")
            time_header = re.sub(r"[\s_()]+", "", headers[0].casefold())
            if time_header not in {"time", "timemin", "timeminutes", "minute", "minutes"}:
                raise ValueError("The first column in row 1 must be a time header, such as Time(min).")
            if len(set(header.casefold() for header in headers)) != len(headers):
                raise ValueError("Give each column in row 1 a unique name.")

            previous_minute = None
            for row in reader:
                line = reader.line_num
                if len(row) != len(headers):
                    raise ValueError(f"Line {line} has {len(row)} fields. The header has {len(headers)} columns.")
                minute = row[0].strip()
                if not minute.isascii() or not minute.isdecimal():
                    raise ValueError(f"Enter a whole minute of 0 or more in the first column on line {line}.")
                minute = int(minute)
                if previous_minute is not None and minute != previous_minute + 1:
                    raise ValueError(f"Line {line} should start with minute {previous_minute + 1}. Found {minute}.")
                previous_minute = minute
        except csv.Error as error:
            raise ValueError(f"Invalid CSV near line {reader.line_num}. {error}.") from error

        stream.seek(0)
        return pd.read_csv(stream, skip_blank_lines=False)


class FlySleepAnalyzer:
    def __init__(self, file_path, bin_duration=30, *, validate_layout=False):
        if not isinstance(bin_duration, (int, np.integer)) or bin_duration < 1:
            raise ValueError("Bin size must be a whole number of at least 1 minute.")

        self.data = _read_validated_csv(file_path) if validate_layout else pd.read_csv(file_path)
        if self.data.empty or self.data.shape[1] < 2:
            raise ValueError("The CSV needs a header, a time column, at least one fly column, and data rows.")
        if not isinstance(self.data.index, pd.RangeIndex):
            raise ValueError("Some CSV rows contain more fields than the header.")

        activity = self.data.iloc[:, 1:]
        numeric = activity.apply(pd.to_numeric, errors="coerce")
        invalid = activity.notna() & ~np.isfinite(numeric)
        if validate_layout:
            invalid |= numeric < 0
        if invalid.to_numpy().any():
            row, column = np.argwhere(invalid.to_numpy())[0]
            expected = "a nonnegative number" if validate_layout else "numeric"
            raise ValueError(
                f"Activity must be {expected}. Check data row {row + 1}, column {activity.columns[column]}."
            )

        self.num_flies = activity.shape[1]
        self.missing_readings = int(activity.isna().to_numpy().sum())
        self.activities = numeric.fillna(0).to_numpy().T
        self.time_interval = bin_duration

    def calculate_sleep(self, inactivity_threshold=0, consecutive_periods=5):
        if not isinstance(consecutive_periods, (int, np.integer)) or consecutive_periods < 1:
            raise ValueError("Minimum inactivity must be a whole number of at least 1 minute.")
        if not np.isfinite(inactivity_threshold):
            raise ValueError("Inactivity threshold must be a finite number.")

        flies, total_minutes = self.activities.shape
        num_bins = (total_minutes + self.time_interval - 1) // self.time_interval
        total_sleep = np.zeros((flies, num_bins), dtype=int)
        bin_size = min(self.time_interval, total_minutes)
        final_bin_is_partial = total_minutes % self.time_interval != 0

        # Match the original scoring, including runs still open in a partial final bin.
        for fly, activity in enumerate(self.activities):
            inactive = activity <= inactivity_threshold
            starts = inactive & ~np.r_[False, inactive[:-1]]
            ends = inactive & ~np.r_[inactive[1:], False]
            starts[::bin_size] = inactive[::bin_size]
            bin_ends = slice(bin_size - 1, None, bin_size)
            ends[bin_ends] = inactive[bin_ends]

            start_minutes = np.flatnonzero(starts)
            end_minutes = np.flatnonzero(ends)
            if final_bin_is_partial and inactive[-1]:
                start_minutes = start_minutes[:-1]
                end_minutes = end_minutes[:-1]
            lengths = end_minutes - start_minutes + 1
            qualifies = lengths >= consecutive_periods
            np.add.at(
                total_sleep[fly], start_minutes[qualifies] // bin_size, lengths[qualifies]
            )
        return total_sleep

    def results_table(self, inactivity_threshold=0, consecutive_periods=5):
        """Return sleep minutes and the input time at the start of each bin."""
        sleep = self.calculate_sleep(inactivity_threshold, consecutive_periods)
        columns = [f"Fly_{fly + 1}" for fly in range(self.num_flies)]
        results = pd.DataFrame(sleep.T, columns=columns)
        results.insert(0, TIME_COLUMN, self.data.iloc[::self.time_interval, 0].to_numpy())
        return results

    def write_results_to_csv(self, output_file, inactivity_threshold=0, consecutive_periods=5):
        self.results_table(inactivity_threshold, consecutive_periods).to_csv(output_file, index=False)


def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("DAM Sleep Analysis")
    root.geometry("860x690")
    root.minsize(720, 600)

    class SleepWindow:
        preview_limit = 100

        def __init__(self):
            self.input_path = tk.StringVar()
            self.bin_size = tk.StringVar(value="30")
            self.sleep_criteria = tk.StringVar(value="5")
            self.status = tk.StringVar(value="Choose a DAM activity CSV to begin.")
            self.preview_info = tk.StringVar(value="Sleep minutes per fly and time bin")
            self.results = None
            self.source = None
            self.output_name = None
            self.executor = ThreadPoolExecutor(max_workers=1)
            self.job = None

            panel = ttk.Frame(root, padding=24)
            panel.pack(fill="both", expand=True)
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(4, weight=1)

            ttk.Label(panel, text="DAM Sleep Analysis", font=("TkDefaultFont", 22, "bold")).grid(
                row=0, column=0, sticky="w", pady=(0, 12)
            )
            input_group = ttk.LabelFrame(panel, text="Activity CSV", padding=12)
            input_group.grid(row=1, column=0, sticky="ew")
            input_group.columnconfigure(0, weight=1)
            self.path_entry = ttk.Entry(input_group, textvariable=self.input_path)
            self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            self.browse_button = ttk.Button(input_group, text="Browse…", command=self.browse)
            self.browse_button.grid(row=0, column=1)
            layout = ttk.Frame(input_group)
            layout.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            ttk.Label(layout, text="Expected CSV layout", font="TkHeadingFont").grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 5)
            )
            sample_columns = (TIME_COLUMN, "Fly_1", "Fly_2")
            sample_rows = ((0, 0, 2), (1, 0, 1), (2, 1, 0))
            sample = ttk.Treeview(
                layout, columns=sample_columns, show="headings", height=len(sample_rows),
                selectmode="none", takefocus=False,
            )
            for column, width in zip(sample_columns, (88, 62, 62)):
                sample.heading(column, text=column, anchor="center")
                sample.column(column, width=width, anchor="center", stretch=False)
            for row in sample_rows:
                sample.insert("", "end", values=row)
            sample.grid(row=1, column=0, sticky="nw", padx=(0, 16))
            ttk.Label(
                layout,
                text="Layout sample",
                justify="left",
            ).grid(row=1, column=1, sticky="nw")

            settings = ttk.LabelFrame(panel, text="Sleep settings", padding=12)
            settings.grid(row=2, column=0, sticky="ew", pady=(12, 0))
            self.setting_entries = []
            for column, (label, variable) in enumerate((
                ("Bin size (min)", self.bin_size),
                ("Sleep criteria (inactivity period, min)", self.sleep_criteria),
            )):
                settings.columnconfigure(column, weight=1)
                ttk.Label(settings, text=label).grid(row=0, column=column, sticky="w", padx=(0, 12))
                entry = ttk.Entry(settings, textvariable=variable, width=12)
                entry.grid(row=1, column=column, sticky="w", pady=(4, 0))
                self.setting_entries.append(entry)

            actions = ttk.Frame(panel)
            actions.grid(row=3, column=0, sticky="ew", pady=12)
            self.run_button = ttk.Button(actions, text="Calculate sleep", command=self.run)
            self.run_button.pack(side="left")
            self.save_button = ttk.Button(actions, text="Save CSV…", command=self.save, state="disabled")
            self.save_button.pack(side="left", padx=8)
            self.progress = ttk.Progressbar(actions, mode="indeterminate", length=130)
            self.progress.pack(side="right")

            preview = ttk.LabelFrame(panel, text="Results preview", padding=12)
            preview.grid(row=4, column=0, sticky="nsew")
            preview.columnconfigure(0, weight=1)
            preview.rowconfigure(1, weight=1)
            ttk.Label(preview, textvariable=self.preview_info).grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
            )
            self.table = ttk.Treeview(preview, show="headings", selectmode="none", height=5)
            self.table.grid(row=1, column=0, sticky="nsew")
            vertical = ttk.Scrollbar(preview, orient="vertical", command=self.table.yview)
            vertical.grid(row=1, column=1, sticky="ns")
            horizontal = ttk.Scrollbar(preview, orient="horizontal", command=self.table.xview)
            horizontal.grid(row=2, column=0, sticky="ew")
            self.table.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
            status = ttk.Label(panel, textvariable=self.status, wraplength=640)
            status.grid(row=5, column=0, sticky="w", pady=(10, 0))
            panel.bind("<Configure>", lambda event: status.configure(wraplength=max(1, event.width - 48)))

            for variable in (self.input_path, self.bin_size, self.sleep_criteria):
                variable.trace_add("write", self.clear_results)
            for entry in (self.path_entry, *self.setting_entries):
                entry.bind("<Return>", lambda _event: self.run())
            root.protocol("WM_DELETE_WINDOW", self.close)
            self.path_entry.focus_set()

        def browse(self):
            current = self.input_path.get()
            start = Path(current).expanduser().parent if current else Path(__file__).resolve().parent
            path = filedialog.askopenfilename(
                parent=root, title="Choose DAM activity CSV", initialdir=start,
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            )
            if path:
                self.input_path.set(path)

        def clear_results(self, *_):
            self.results = None
            self.save_button.state(["disabled"])
            self.table.delete(*self.table.get_children())
            self.table["columns"] = ()
            self.preview_info.set("Sleep minutes per fly and time bin")
            self.status.set(
                "Ready to calculate." if self.input_path.get().strip() else "Choose a DAM activity CSV to begin."
            )

        def run(self):
            if self.job is not None:
                return
            path = self.input_path.get().strip()
            try:
                if not path or not Path(path).expanduser().is_file():
                    raise ValueError("Choose an existing DAM activity CSV.")
                try:
                    size = int(self.bin_size.get())
                    minimum = int(self.sleep_criteria.get())
                except ValueError:
                    raise ValueError("Enter whole numbers for bin size and sleep criteria.") from None
                if size < 1:
                    raise ValueError("Bin size must be at least 1 minute.")
                if not 1 <= minimum <= size:
                    raise ValueError("Sleep criteria must be at least 1 minute and fit within the bin size.")
            except (ValueError, OSError) as error:
                messagebox.showerror("Check analysis settings", str(error), parent=root)
                return

            self.clear_results()
            self.source = Path(path).expanduser().absolute()
            self.output_name = f"{self.source.stem}_sleep_{size}min.csv"
            self.status.set(f"Calculating sleep for {self.source.name}…")
            self.set_busy(True)
            self.job = self.executor.submit(self.analyze, self.source, size, minimum)
            root.after(50, self.check_job)

        @staticmethod
        def analyze(source, size, minimum):
            analyzer = FlySleepAnalyzer(source, size, validate_layout=True)
            results = analyzer.results_table(consecutive_periods=minimum)
            return results, len(analyzer.data), analyzer.missing_readings

        def set_busy(self, busy):
            state = ["disabled"] if busy else ["!disabled"]
            for widget in (self.path_entry, *self.setting_entries, self.browse_button, self.run_button):
                widget.state(state)
            if busy:
                self.progress.start(12)
            else:
                self.progress.stop()

        def check_job(self):
            if not self.job.done():
                root.after(50, self.check_job)
                return
            job, self.job = self.job, None
            self.set_busy(False)
            try:
                self.results, minutes, missing = job.result()
            except (OSError, ValueError) as error:
                self.status.set("Analysis failed. Check the file against the expected CSV layout.")
                messagebox.showerror("Could not calculate sleep", str(error), parent=root)
                return

            preview = self.results.head(self.preview_limit)
            self.table["columns"] = list(preview.columns)
            self.table.heading(TIME_COLUMN, text="Bin start (min)")
            self.table.column(TIME_COLUMN, width=112, anchor="e", stretch=False)
            for column in preview.columns[1:]:
                self.table.heading(column, text=column)
                self.table.column(column, width=74, anchor="e", stretch=False)
            for row in preview.itertuples(index=False, name=None):
                self.table.insert("", "end", values=row)
            self.table.xview_moveto(0)
            self.table.yview_moveto(0)
            flies = self.results.shape[1] - 1
            summary = f"{flies:,} flies  ·  {minutes:,} recorded minutes  ·  {len(self.results):,} bins"
            if len(preview) < len(self.results):
                summary += f"  ·  First {len(preview)} bins shown"
            self.preview_info.set(summary)
            self.status.set(
                f"Ready to export. {missing:,} missing activity readings were treated as zero."
                if missing else "Ready to export. The CSV includes all bins in minutes."
            )
            self.save_button.state(["!disabled"])

        def save(self):
            if self.results is None:
                return
            path = filedialog.asksaveasfilename(
                parent=root, title="Save sleep results", initialdir=self.source.parent,
                initialfile=self.output_name, defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            )
            if not path:
                return
            destination = Path(path)
            try:
                if destination.exists() and destination.samefile(self.source):
                    raise ValueError("Choose a different filename to preserve the activity CSV.")
                self.export(destination)
            except (OSError, ValueError) as error:
                messagebox.showerror("Could not save results", str(error), parent=root)
                return
            self.status.set(f"Saved {destination}")
            self.output_name = destination.name

        def export(self, destination):
            temporary_path = None
            try:
                with NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                    temporary_path = Path(temporary.name)
                self.results.to_csv(temporary_path, index=False)
                temporary_path.replace(destination)
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

        def close(self):
            if self.job is not None and not self.job.done():
                self.status.set("Analysis is still running. You can close the window when it finishes.")
                return
            self.executor.shutdown(wait=False)
            root.destroy()

    SleepWindow()
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
