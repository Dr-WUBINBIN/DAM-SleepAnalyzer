
# Binbin Wu complete this sleep_analysis script on 6/30/2024.
# Binbin Wu have this script copyright.
# Please cite related papers if you are using this script or revised script to analyze sleep.


import pandas as pd
import numpy as np

class FlySleepAnalyzer:
    def __init__(self, file_path, bin_duration=30):
        self.data = pd.read_csv(file_path)
        print("Columns in the file:", self.data.columns)  # Check loaded columns
        self.num_flies = self.data.shape[1] - 1  # Calculate number of flies
        self.activities = self.data.iloc[:, 1:].fillna(0).values.T  # Extract activity data and transpose it
        self.time_interval = bin_duration  # Define time interval in minutes

    def calculate_sleep(self, inactivity_threshold=0, consecutive_periods=5):
        flies, total_min = self.activities.shape
        
        # Calculate number of 30-minute intervals
        num_intervals = int(np.ceil(total_min / self.time_interval))
        
        # Initialize sleep time array
        total_sleep_time = np.zeros((flies, num_intervals), dtype=int)
        
        # Calculate sleep per 30 minutes interval
        for fly in range(flies):
            consecutive_count = 0
            interval_index = 0
            for i in range(total_min):
                if self.activities[fly, i] <= inactivity_threshold:
                    consecutive_count += 1
                else:
                    if consecutive_count >= consecutive_periods:
                        total_sleep_time[fly,interval_index] += consecutive_count
                    consecutive_count = 0
                
                # Check if 30 minutes have passed
                if (i + 1) % self.time_interval == 0:
                    if consecutive_count >= consecutive_periods:
                        total_sleep_time[fly, interval_index] += consecutive_count
                    consecutive_count = 0
                    interval_index += 1
            
        
        return total_sleep_time

    def write_results_to_csv(self, output_file):
        total_sleep_time = self.calculate_sleep()
        
        # Prepare data for CSV output
        data_dict = {}
        for fly in range(total_sleep_time.shape[0]):
            data_dict[f"Fly_{fly + 1}"] = total_sleep_time[fly, :]
        
        # Convert to DataFrame
        df = pd.DataFrame(data_dict)
        
        # Write to CSV
        df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")

# Usage example
file_path = 'DAM_Data.csv'
output_file = 'fly_sleep_30min_result.csv'

# Initialize and run the sleep analysis
analyzer = FlySleepAnalyzer(file_path, bin_duration=30)
analyzer.write_results_to_csv(output_file)
