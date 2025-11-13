import time
from serial import Serial
from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType
from pylsl import StreamInfo, StreamOutlet

# --- Setup ---
stream_name = 'ShimmerData_5Channel'
stream_type = 'Signals'
channel_count = 5
sample_rate = 51.2
channel_format = 'float32'
source_id = 'my-shimmer-1234'

info = StreamInfo(stream_name, stream_type, channel_count, sample_rate, channel_format, source_id)
#Add PPG later
channels = info.desc().append_child("channels")
ch_names = ['GSR', 'PPG', 'Accel_X', 'Accel_Y', 'Accel_Z']
ch_units = ['kOhms', 'raw', 'm/s^2', 'm/s^2', 'm/s^2'] #add 'raw'

for name, unit in zip(ch_names, ch_units):
    channels.append_child("channel") \
            .append_child_value("label", name) \
            .append_child_value("type", stream_type) \
            .append_child_value("unit", unit)

outlet = StreamOutlet(info)

_sensor_errors = set()


def shimmer_callback(pkt: DataPacket) -> None:
    global _sensor_errors
    
    try:
        gsr_data = pkt[EChannelType.GSR_RAW]
    except Exception:
        if 'gsr' not in _sensor_errors:
            print("ERROR: GSR (INTERNAL_ADC_13) not found. Check Consensys config.")
            _sensor_errors.add('gsr')
        gsr_data = 0.0

    try:
        ppg_data = pkt[EChannelType.INTERNAL_ADC_12] 
    except Exception:
        if 'ppg' not in _sensor_errors:
            print("ERROR: PPG (INTERNAL_ADC_12) not found. Check Consensys config.")
            _sensor_errors.add('ppg')
        ppg_data = 0.0
        
    try:
        accel_x = pkt[EChannelType.ACCEL_LN_X]
        accel_y = pkt[EChannelType.ACCEL_LN_Y]
        accel_z = pkt[EChannelType.ACCEL_LN_Z]
    except Exception:
        if 'accel' not in _sensor_errors:
            print("ERROR: Accelerometer (ACCEL_LN_X/Y/Z) not found. Check Consensys config.")
            _sensor_errors.add('accel')
        accel_x, accel_y, accel_z = 0.0, 0.0, 0.0

    try: #add ppg later
        sample = [gsr_data, ppg_data, accel_x, accel_y, accel_z]
        outlet.push_sample(sample)
    except Exception as e:
        if 'push' not in _sensor_errors:
            print(f"Error pushing LSL sample: {e}")
            _sensor_errors.add('push')

# --- Connection Loop ---
if __name__ == '__main__':
    
    serial_port = 'COM9' 
    print(f"Connecting to Shimmer on {serial_port}...")
    
    shim_dev = None
    serial_conn = None

    try:
        serial_conn = Serial(serial_port, DEFAULT_BAUDRATE)
        shim_dev = ShimmerBluetooth(serial_conn)
        shim_dev.initialize()

        x,y,z = shim_dev.get_inquiry()
        print(z)

        print(f"Connected to device: {shim_dev.get_device_name()}")

        shim_dev.add_stream_callback(shimmer_callback)
        print("\nStarting LSL stream. Open LabRecorder now.")
        print(f"Stream name: '{stream_name}' ({channel_count} channels)")
        shim_dev.start_streaming()

        print("\n--- STREAMING ---")
        print("Press Ctrl+C to stop.")
        print("Errors will appear below if sensors are missing from config.")
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Cleaning up and shutting down...")
        if 'shim_dev' in locals() and shim_dev:
            shim_dev.stop_streaming()
            shim_dev.shutdown()
        if 'serial_conn' in locals() and serial_conn and serial_conn.is_open:
            serial_conn.close()
        print("Stream stopped.")