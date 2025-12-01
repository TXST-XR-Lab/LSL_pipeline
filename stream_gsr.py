import time
from serial import Serial
from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType
from pylsl import StreamInfo, StreamOutlet

SERIAL_PORT = 'COM10'
STREAM_NAME = 'Shimmer_All_Sensors'
SOURCE_ID = 'shimmer_full_6621'

GSR_REF_RESISTORS = [40.2, 287.0, 1000.0, 3300.0] 
ACCEL_OFFSET = 2048     
ACCEL_SENSITIVITY = 830.0 
GYRO_SENSITIVITY = 131.0 
MAG_SENSITIVITY = 1100.0 

channel_count = 13 
info = StreamInfo(STREAM_NAME, 'Signals', channel_count, 51.2, 'float32', SOURCE_ID)

channels = info.desc().append_child("channels")
ch_conf = [
    ("GSR_Skin_Resistance", "kOhms"),
    ("GSR_Range", "no_units"),      
    ("PPG_A12", "mV"),             
    ("Accel_LN_X", "m/s^2"),
    ("Accel_LN_Y", "m/s^2"),
    ("Accel_LN_Z", "m/s^2"),
    ("Gyro_X", "deg/s"),
    ("Gyro_Y", "deg/s"),
    ("Gyro_Z", "deg/s"),
    ("Mag_X", "local_flux"),
    ("Mag_Y", "local_flux"),
    ("Mag_Z", "local_flux"),
    ("Battery", "mV")
]

for label, unit in ch_conf:
    channels.append_child("channel") \
            .append_child_value("label", label) \
            .append_child_value("unit", unit) \
            .append_child_value("type", "Signals")

outlet = StreamOutlet(info)
_sensor_errors = set()

def shimmer_callback(pkt: DataPacket) -> None:
    global _sensor_errors
    
    gsr_k_ohms = 0.0
    gsr_range = 0.0
    ppg_mv = 0.0
    ax, ay, az = 0.0, 0.0, 0.0
    gx, gy, gz = 0.0, 0.0, 0.0
    mx, my, mz = 0.0, 0.0, 0.0
    batt_mv = 0.0

    try:
        raw_gsr_int = pkt[EChannelType.GSR_RAW]
        range_index = (raw_gsr_int >> 14) & 0x03
        gsr_range = float(range_index)
        
        raw_val = raw_gsr_int & 0x3FFF
        volts = raw_val * (3.0 / 4095.0)
        rf = GSR_REF_RESISTORS[range_index]
        
        if volts <= 0.5: 
            gsr_k_ohms = 0.0
        else:
            gsr_k_ohms = rf / ((volts / 0.5) - 1.0)
    except:
        if 'gsr' not in _sensor_errors: _sensor_errors.add('gsr')

    try:
        raw_ppg = pkt[EChannelType.INTERNAL_ADC_12] 
        ppg_mv = raw_ppg * (3000.0 / 4095.0)
    except:
        pass 

    try:
        ax = (pkt[EChannelType.ACCEL_LN_X] - ACCEL_OFFSET) / ACCEL_SENSITIVITY * 9.81
        ay = (pkt[EChannelType.ACCEL_LN_Y] - ACCEL_OFFSET) / ACCEL_SENSITIVITY * 9.81
        az = (pkt[EChannelType.ACCEL_LN_Z] - ACCEL_OFFSET) / ACCEL_SENSITIVITY * 9.81
    except:
        if 'accel' not in _sensor_errors: _sensor_errors.add('accel')

    try:
        gx = pkt[EChannelType.GYRO_MPU9150_X] / GYRO_SENSITIVITY
        gy = pkt[EChannelType.GYRO_MPU9150_Y] / GYRO_SENSITIVITY
        gz = pkt[EChannelType.GYRO_MPU9150_Z] / GYRO_SENSITIVITY
    except:
        if 'gyro' not in _sensor_errors: _sensor_errors.add('gyro')

    try:
        mx = pkt[EChannelType.MAG_LSM303DLHC_X] / MAG_SENSITIVITY
        my = pkt[EChannelType.MAG_LSM303DLHC_Y] / MAG_SENSITIVITY
        mz = pkt[EChannelType.MAG_LSM303DLHC_Z] / MAG_SENSITIVITY
    except:
        if 'mag' not in _sensor_errors: _sensor_errors.add('mag')

    try:
        raw_batt = pkt[EChannelType.VBATT]
        batt_mv = raw_batt * (6000.0 / 4095.0)
    except:
        pass

    try:
        sample = [gsr_k_ohms, gsr_range, ppg_mv, ax, ay, az, gx, gy, gz, mx, my, mz, batt_mv]
        outlet.push_sample(sample)
    except Exception as e:
        if 'push' not in _sensor_errors:
            print(f"LSL Error: {e}")
            _sensor_errors.add('push')

if __name__ == '__main__':
    print(f"Connecting to Shimmer on {SERIAL_PORT}...")
    
    shim_dev = None
    serial_conn = None

    try:
        serial_conn = Serial(SERIAL_PORT, DEFAULT_BAUDRATE)
        
        shim_dev = ShimmerBluetooth(serial_conn)
        shim_dev.initialize()
        print(f"Connected: {shim_dev.get_device_name()}")
        
        shim_dev.add_stream_callback(shimmer_callback)
        shim_dev.start_streaming()

        print("\n--- STREAMING LIVE ---")
        print("Channels: GSR, PPG, Accel, Gyro, Mag, Battery")
        print("Press Ctrl+C to stop.\n")
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Cleaning up...")
        if shim_dev:
            shim_dev.stop_streaming()
            shim_dev.shutdown()
        if serial_conn and serial_conn.is_open:
            serial_conn.close()
        print("Done.")