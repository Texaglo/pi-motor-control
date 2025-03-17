#!/usr/bin/env python3
import os
import json
import sys
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuration file path
CONFIG_FILE = 'motor_config.json'

# Default configuration for motor pins
DEFAULT_CONFIG = {
    'motor1': {'step_pin': 17, 'dir_pin': 27},
    'motor2': {'step_pin': 22, 'dir_pin': 23}
}

print("Starting Raspberry Pi Motor Control System...")
print(f"Python version: {sys.version}")
print(f"Running as user ID: {os.geteuid()}")

# Function to load pin configuration
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # If config file doesn't exist, create it with default values
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG

# Function to save pin configuration
def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Mock GPIO class for when real GPIO access fails
class MockGPIO:
    OUT = 1
    IN = 0
    HIGH = 1
    LOW = 0
    BCM = 11
    BOARD = 10
    
    @staticmethod
    def setmode(mode):
        print(f"Mock: GPIO.setmode({mode})")
        
    @staticmethod
    def setup(pin, mode):
        print(f"Mock: GPIO.setup({pin}, {mode})")
        
    @staticmethod
    def output(pin, value):
        print(f"Mock: GPIO.output({pin}, {value})")
        
    @staticmethod
    def cleanup():
        print("Mock: GPIO.cleanup()")

# Global variables
GPIO = None
GPIO_AVAILABLE = False
motor_config = load_config()
active_pins = set()
gpio_initialized = False

# Try to import GPIO, fall back to mock if not available
try:
    import RPi.GPIO as GPIO
    print("RPi.GPIO imported successfully")
    
    # Test GPIO access - this will fail if we don't have proper permissions
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)  # Test with pin 17
        GPIO.cleanup()
        GPIO_AVAILABLE = True
        print("GPIO access confirmed")
    except Exception as e:
        print(f"GPIO access test failed: {e}")
        print("Falling back to mock GPIO mode")
        GPIO = MockGPIO
        GPIO_AVAILABLE = False
except (ImportError, RuntimeError) as e:
    print(f"Error importing RPi.GPIO: {e}")
    GPIO = MockGPIO
    GPIO_AVAILABLE = False
    print("Using MockGPIO for testing")

# Initialize GPIO
def init_gpio():
    global gpio_initialized, motor_config, active_pins, GPIO, GPIO_AVAILABLE
    
    try:
        print(f"Initializing GPIO with config: {motor_config}")
        # Clean up any existing GPIO configuration
        GPIO.cleanup()
        active_pins = set()
        
        # Set GPIO mode
        GPIO.setmode(GPIO.BCM)
        
        # Setup motor pins from configuration
        for motor, pins in motor_config.items():
            step_pin = pins['step_pin']
            dir_pin = pins['dir_pin']
            
            GPIO.setup(step_pin, GPIO.OUT)
            GPIO.setup(dir_pin, GPIO.OUT)
            GPIO.output(step_pin, GPIO.LOW)
            GPIO.output(dir_pin, GPIO.LOW)
            active_pins.add(step_pin)
            active_pins.add(dir_pin)
        
        gpio_initialized = True
        print(f"GPIO initialized with configuration: {motor_config}")
        print(f"Active pins: {active_pins}")
        return True
    except Exception as e:
        print(f"Error initializing GPIO: {e}")
        # If using mock or if it's a permission issue, pretend initialization succeeded
        if not GPIO_AVAILABLE or "GPIO not allocated" in str(e):
            if "GPIO not allocated" in str(e):
                print("GPIO permission error detected, switching to mock mode")
                GPIO = MockGPIO
                GPIO_AVAILABLE = False
            
            # In mock mode, we still want to pretend initialization succeeded
            gpio_initialized = True
            print("Mock GPIO initialized successfully")
            return True
        return False

# Initialize GPIO on startup
init_result = init_gpio()
print(f"GPIO initialization result: {init_result}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move_motor', methods=['POST'])
def move_motor():
    global gpio_initialized, motor_config
    
    if not gpio_initialized:
        init_gpio()
    
    motor = request.json.get('motor')
    steps = request.json.get('steps', 100)
    delay = request.json.get('delay', 0.001)
    
    # Validate input
    if motor not in motor_config:
        return jsonify({'status': 'error', 'message': f'Invalid motor: {motor}'})
    
    try:
        steps = int(steps)
        delay = float(delay)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid steps or delay value'})
    
    # Set direction based on steps value
    direction = steps > 0
    steps = abs(steps)
    
    try:
        # Get pin configuration for the selected motor
        pins = motor_config[motor]
        step_pin = pins['step_pin']
        dir_pin = pins['dir_pin']
        
        # Set direction
        GPIO.output(dir_pin, GPIO.HIGH if direction else GPIO.LOW)
        
        # Step the motor
        for _ in range(steps):
            GPIO.output(step_pin, GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(step_pin, GPIO.LOW)
            time.sleep(delay)
        
        return jsonify({
            'status': 'success',
            'message': f'Moved {motor} {steps} steps {"forward" if direction else "backward"}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error moving motor: {str(e)}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

@app.route('/stop_all', methods=['POST'])
def stop_all():
    global gpio_initialized
    
    try:
        if gpio_initialized:
            GPIO.cleanup()
            gpio_initialized = False
            print("Emergency stop: All GPIO pins released")
        
        return jsonify({
            'status': 'success',
            'message': 'Emergency stop activated. All motors stopped.',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error during emergency stop: {str(e)}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

@app.route('/get_config', methods=['GET'])
def get_config():
    global motor_config
    
    # Create a mapping of physical pin numbers to BCM pin numbers
    bcm_to_physical = {
        2: 3, 3: 5, 4: 7, 17: 11, 27: 13, 22: 15, 10: 19, 9: 21, 11: 23, 5: 29, 
        6: 31, 13: 33, 19: 35, 26: 37, 14: 8, 15: 10, 18: 12, 23: 16, 24: 18, 
        25: 22, 8: 24, 7: 26, 12: 32, 16: 36, 20: 38, 21: 40
    }
    
    # Add physical pin numbers to the configuration
    config_with_physical = {}
    for motor, pins in motor_config.items():
        config_with_physical[motor] = {
            'step_pin': pins['step_pin'],
            'dir_pin': pins['dir_pin'],
            'step_pin_physical': bcm_to_physical.get(pins['step_pin'], 'Unknown'),
            'dir_pin_physical': bcm_to_physical.get(pins['dir_pin'], 'Unknown')
        }
    
    return jsonify({
        'status': 'success',
        'config': config_with_physical
    })

@app.route('/gpio_info', methods=['GET'])
def gpio_info():
    global gpio_initialized, motor_config, active_pins
    
    if not gpio_initialized:
        init_gpio()
    
    # Create a mapping of physical pin numbers to BCM pin numbers
    bcm_to_physical = {
        2: 3, 3: 5, 4: 7, 17: 11, 27: 13, 22: 15, 10: 19, 9: 21, 11: 23, 5: 29, 
        6: 31, 13: 33, 19: 35, 26: 37, 14: 8, 15: 10, 18: 12, 23: 16, 24: 18, 
        25: 22, 8: 24, 7: 26, 12: 32, 16: 36, 20: 38, 21: 40
    }
    
    # Create mapping of pins to motors
    pin_to_motor = {}
    for motor, pins in motor_config.items():
        pin_to_motor[pins['step_pin']] = f"{motor} step"
        pin_to_motor[pins['dir_pin']] = f"{motor} direction"
    
    # Collect GPIO pin information
    gpio_pins = []
    for bcm_pin in range(28):  # Raspberry Pi has BCM pins 0-27
        pin_info = {
            'bcm_pin': bcm_pin,
            'physical_pin': bcm_to_physical.get(bcm_pin, 'N/A'),
            'active': bcm_pin in active_pins,
            'function': pin_to_motor.get(bcm_pin, 'Unused'),
            'is_motor_pin': bcm_pin in active_pins
        }
        gpio_pins.append(pin_info)
    
    # Get all available BCM pins for dropdowns
    available_pins = []
    for pin in range(28):
        # Skip pins that are currently in use by another motor
        if pin in active_pins:
            for motor, pins in motor_config.items():
                if pin == pins['step_pin'] or pin == pins['dir_pin']:
                    available_pins.append({
                        'bcm_pin': pin, 
                        'physical_pin': bcm_to_physical.get(pin, 'N/A'),
                        'in_use': True,
                        'used_by': pin_to_motor.get(pin, 'Unknown')
                    })
                    break
        else:
            available_pins.append({
                'bcm_pin': pin, 
                'physical_pin': bcm_to_physical.get(pin, 'N/A'),
                'in_use': False,
                'used_by': None
            })
    
    return jsonify({
        'status': 'success',
        'gpio_initialized': gpio_initialized,
        'gpio_available': GPIO_AVAILABLE,
        'mock_mode': not GPIO_AVAILABLE,
        'message': 'Running in mock mode - no real GPIO access' if not GPIO_AVAILABLE else 'Real GPIO mode',
        'motor_config': motor_config,
        'active_pins': list(active_pins),
        'gpio_pins': gpio_pins,
        'available_pins': available_pins
    })

@app.route('/update_pins', methods=['POST'])
def update_pins():
    global motor_config, gpio_initialized
    
    try:
        # Get the new pin configuration from the request
        new_config = request.json
        
        if not new_config:
            return jsonify({
                'status': 'error',
                'message': 'No configuration provided'
            })
        
        # Validate the configuration
        required_keys = ['motor', 'step_pin', 'dir_pin']
        for key in required_keys:
            if key not in new_config:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {key}'
                })
        
        motor = new_config['motor']
        step_pin = int(new_config['step_pin'])
        dir_pin = int(new_config['dir_pin'])
        
        # Check if motor exists
        if motor not in motor_config:
            return jsonify({
                'status': 'error',
                'message': f'Invalid motor: {motor}'
            })
        
        # Check for pin conflicts with other motors
        for other_motor, pins in motor_config.items():
            if other_motor == motor:
                continue
            
            if step_pin in [pins['step_pin'], pins['dir_pin']] or dir_pin in [pins['step_pin'], pins['dir_pin']]:
                return jsonify({
                    'status': 'error',
                    'message': f'Pin conflict with {other_motor}. Choose different pins.'
                })
        
        # Check if step and dir pins are the same
        if step_pin == dir_pin:
            return jsonify({
                'status': 'error',
                'message': 'Step and direction pins cannot be the same'
            })
        
        # Update the configuration
        motor_config[motor]['step_pin'] = step_pin
        motor_config[motor]['dir_pin'] = dir_pin
        
        # Save the configuration
        save_config(motor_config)
        
        # Reinitialize GPIO with the new configuration
        gpio_initialized = False
        init_result = init_gpio()
        
        return jsonify({
            'status': 'success',
            'message': f'Pin configuration for {motor} updated successfully',
            'new_config': motor_config[motor],
            'gpio_initialized': gpio_initialized
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error updating pin configuration: {str(e)}'
        })

# Get list of available GPIO pins (useful for dropdown selection)
@app.route('/available_pins', methods=['GET'])
def available_pins():
    global motor_config, active_pins
    
    # Create a mapping of physical pin numbers to BCM pin numbers
    bcm_to_physical = {
        2: 3, 3: 5, 4: 7, 17: 11, 27: 13, 22: 15, 10: 19, 9: 21, 11: 23, 5: 29, 
        6: 31, 13: 33, 19: 35, 26: 37, 14: 8, 15: 10, 18: 12, 23: 16, 24: 18, 
        25: 22, 8: 24, 7: 26, 12: 32, 16: 36, 20: 38, 21: 40
    }
    
    # Get all available BCM pins
    available_pins = []
    for pin in range(28):
        in_use = False
        used_by = None
        
        # Check if pin is used by any motor
        for motor, pins in motor_config.items():
            if pin == pins['step_pin']:
                in_use = True
                used_by = f"{motor} step"
                break
            elif pin == pins['dir_pin']:
                in_use = True
                used_by = f"{motor} direction"
                break
        
        available_pins.append({
            'bcm_pin': pin,
            'physical_pin': bcm_to_physical.get(pin, 'N/A'),
            'in_use': in_use,
            'used_by': used_by
        })
    
    return jsonify({
        'status': 'success',
        'available_pins': available_pins
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True) 