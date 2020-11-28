import json
import uuid
import random
import serial
import logging
import threading
import paho.mqtt.client as mqtt

# CONST VALUES
SERIAL_PORT = '/dev/ttyS0'
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 100
MQTT_HOST = 'localhost'
MQTT_PORT = 1883

DESTINATION = '427'
sclient = None
logger = init_logger()

def init_logger():
    '''
    Initiate main logger.
    '''
    _logger = logging.getLogger('Main')
    _logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="[ %(asctime)s ] %(message)s")
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    _logger.addHandler(stream_handler)
    return _logger

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info('MQTT Connected Successfully (to {}:{})'.format(MQTT_HOST, MQTT_PORT))
    else:
        logger.info('MQTT Connection Failed!')
        
def on_message(client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        
        code: int
        if msg.topic == '/beverage/location':
            code = handle_beverage(loc=data['location'], error_padding=5)
        elif msg.topic == '/room':
            code = handle_room(label=data['label'])
        elif msg.topic == '/qr':
            code = handle_qr()
        else:
            return
        logger.info('code:', code)
        
        if code == 3:
            client.unsubscribe('/beverage/location')
            logger.info('MQTT unsubscribed topic "/beverage/location".')
        elif code == 4:
            client.unsubscribe('/room')
            logger.info('MQTT unsubscribed topic "/room".')
        
def handle_beverage(loc, center=320, error_padding=5):
    x_range = (center - error_padding, center + error_padding)
    code = 0
    if loc < x_range[0]:
        sclient.write(serial.to_bytes([0x01]))
        code = 1
    elif loc > x_range[1]:
        sclient.write(serial.to_bytes([0x02]))
        code = 2
    else:
        sclient.write(serial.to_bytes([0x03]))
        code = 3
    return code
        
def handle_room(label):
    if label == DESTINATION:
        sclient.write(serial.to_bytes([0x04]))
        return 4
        
def handle_qr():
    sclient.write(serial.to_bytes([0x05]))
    return 5

if __name__ == '__main__':
    # Serial Connection
    sclient = serial.Serial(port=SERIAL_PORT, baudrate=SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
    if not sclient.isOpen():
        logger.info('Cannot open the serial port {} .'.format(SERIAL_PORT))
    
    # MQTT Connection
    client = mqtt.Client(str(uuid.uuid1()))
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)

    # MQTT Loop
    client.subscribe('/beverage/location', 1)
    client.subscribe('/room', 1)
    client.subscribe('/qr', 1)
    client.subscribe('/supervisor', 2)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info('KeyboardInterrupt occured.')
        client.disconnect()
        sclient.close()
