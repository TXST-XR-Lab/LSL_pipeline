import pyxdf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import glob
#Change target path to your own folder where the xdf file is located
TARGET_PATH = r"C:\LabData\sub-P001\ses-S001\gsr"

def inspect_shimmer_data():
    print(f"--- Scanning Location: {TARGET_PATH} ---")
    
    if os.path.isdir(TARGET_PATH):
        search_pattern = os.path.join(TARGET_PATH, "*.xdf")
        files = glob.glob(search_pattern)
        
        if not files:
            print("CRITICAL ERROR: No .xdf files found in this folder!")
            return
            
        filename = max(files, key=os.path.getmtime)
        print(f"Auto-selected latest file: {os.path.basename(filename)}")
    else:
        filename = TARGET_PATH

    try:
        streams, header = pyxdf.load_xdf(filename)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    shimmer_stream = None
    print(f"Found {len(streams)} streams in file:")
    
    for s in streams:
        name = s['info']['name'][0]
        cnt = s['info']['channel_count'][0]
        print(f" - Stream Name: '{name}' (Channels: {cnt})")
        
        if name == 'Shimmer_All_Sensors':
            shimmer_stream = s

    if not shimmer_stream:
        print("\nCRITICAL: Could not find stream named 'Shimmer_All_Sensors'.")
        print("Did you check the box in LabRecorder?")
        return

    data = shimmer_stream['time_series'] 
    times = shimmer_stream['time_stamps']
    
    if len(times) > 0:
        times = times - times[0]
        duration = times[-1]
        print(f"\nData Loaded: {len(times)} samples over {duration:.2f} seconds.")
    else:
        print("Stream is empty!")
        return

    gsr = data[:, 0]
    ppg = data[:, 2]
    accel_x, accel_y, accel_z = data[:, 3], data[:, 4], data[:, 5]
    gyro_x, gyro_y, gyro_z = data[:, 6], data[:, 7], data[:, 8]

    print("Plotting data...")
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(12, 10))
    fig.suptitle(f"Shimmer Data Analysis: {os.path.basename(filename)}")

    axes[0].plot(times, gsr, color='purple', label='GSR Skin Resistance')
    axes[0].set_ylabel('Resistance (kOhms)')
    axes[0].set_title('Galvanic Skin Response (Stress)')
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(times, ppg, color='red', label='PPG Raw')
    axes[1].set_ylabel('Voltage (mV)')
    axes[1].set_title('PPG (Heart Rate / Vasoconstriction)')
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(times, accel_x, label='X', linewidth=1)
    axes[2].plot(times, accel_y, label='Y', linewidth=1)
    axes[2].plot(times, accel_z, label='Z', linewidth=1)
    axes[2].set_ylabel('Accel (m/s^2)')
    axes[2].set_title('Accelerometer (Movement)')
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3)

    axes[3].plot(times, gyro_x, label='X', linewidth=1)
    axes[3].plot(times, gyro_y, label='Y', linewidth=1)
    axes[3].plot(times, gyro_z, label='Z', linewidth=1)
    axes[3].set_ylabel('Gyro (deg/s)')
    axes[3].set_title('Gyroscope (Head Turn/Rotation)')
    axes[3].set_xlabel('Time (seconds)')
    axes[3].legend(loc='upper right')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    export = input("\nDo you want to export this to CSV? (y/n): ")
    if export.lower() == 'y':
        cols = [
            "GSR_kOhms", "GSR_Range", "PPG_mV", 
            "Accel_X", "Accel_Y", "Accel_Z",
            "Gyro_X", "Gyro_Y", "Gyro_Z",
            "Mag_X", "Mag_Y", "Mag_Z", "Battery_mV"
        ]
        df = pd.DataFrame(data, columns=cols)
        df.insert(0, "Time", times)
        csv_name = filename.replace(".xdf", ".csv")
        df.to_csv(csv_name, index=False)
        print(f"Saved to {csv_name}")

if __name__ == "__main__":
    inspect_shimmer_data()