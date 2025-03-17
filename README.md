# Raspberry Pi Motor Control System

A web-based interface for controlling stepper motors connected to a Raspberry Pi GPIO pins.

## Features

- **Web Interface**: Control motors from any device with a web browser
- **Dynamic Pin Assignment**: Easily change GPIO pin assignments through the web interface
- **Visual GPIO Representation**: Interactive visualization of all Raspberry Pi GPIO pins
- **Real-time Updates**: Pin status updates showing which pins are active
- **Configurable Control**: Adjustable step count for precise motor control
- **Emergency Stop**: Immediate shutdown of all motors

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- Stepper motor drivers (compatible with step/direction control)
- Stepper motors
- Power supply for the motors

## Software Requirements

- Python 3.6+
- Flask
- RPi.GPIO library

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/pi-motor-control.git
   cd pi-motor-control
   ```

2. Install required Python packages:
   ```
   pip3 install flask RPi.GPIO
   ```

3. Run the application:
   ```
   sudo python3 app.py
   ```

4. Access the web interface by navigating to:
   ```
   http://[your-raspberry-pi-ip]:5000
   ```

## Usage

### Motor Control
- Use the forward/backward buttons to control motor movement
- Set the number of steps to control the distance
- Use preset step values for common movements

### Pin Assignment
1. Click "Edit Pins" next to a motor
2. Select the desired GPIO pins for step and direction control
3. Click "Save Changes" to apply the new configuration

### Emergency Stop
- Press the "EMERGENCY STOP" button to immediately halt all motor activity

## Configuration

The system uses a JSON file (`motor_config.json`) to store pin configurations, which persists between restarts.

Default configuration:
```json
{
  "motor1": {"step_pin": 17, "dir_pin": 27},
  "motor2": {"step_pin": 22, "dir_pin": 23}
}
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 