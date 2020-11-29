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
SUB_TOPICS = [
    ('/beverage/location', 1),
    ('/room', 1),
    ('/qr', 1),
    ('/supervisor', 2)
]

# Global Variables
destination = '427'
start_label = '000'
sclient = None
logger = init_logger()
location_status = 'STARTING_POINT' # STARTING_POINT / DESTINATION

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
    global location_status

    # Decoding message
    data = json.loads(msg.payload.decode('utf-8'))
    logger.info('Message arrived : {}'.format(msg.payload.decode('utf-8')))
    
    # Get code which will be sent to STM board.
    code: int
    if msg.topic == '/beverage/location':
        code = handle_beverage(loc=data['location'], error_padding=5)
    elif msg.topic == '/room':
        code = handle_room(label=data['label'])
    elif msg.topic == '/qr':
        code = handle_qr()
    elif msg.topic == '/supervisor':
        handle_supervisor(payload=data)
    else:
        return

    # Preprocessing
    if code == '3':
        client.unsubscribe('/beverage/location')
        logger.info('MQTT unsubscribed topic "/beverage/location".')
    elif code == '5':
        if location_status == 'DESTINATION':
            return
        location_status = 'DESTINATION'
    elif code == '6':
        if location_status == 'STARTING_POINT':
            return
        location_status = 'STARTING_POINT'

    # Send code to STM board.
    sclient.write(serial.to_bytes([int(code, 16)]))
    logger.info('Code {} sent.'.format(code))
        
def handle_beverage(loc, center=320, error_padding=5):
    x_range = (center - error_padding, center + error_padding)
    code = '0'
    if loc < x_range[0]:
        code = '1'
    elif loc > x_range[1]:
        code = '2'
    else:
        code = '3'
    return code
        
def handle_room(label):
    if label == destination:
        logger.info('Arrived at the destination {} !'.format(destination))
        return '5'
    elif label == start_label:
        logger.info('Arrived at the Starting Point!')
        return '6'
        
def handle_qr():
    logger.info('QR Code detected!')
    return '4'

def handle_supervisor(payload):
    global destination

    try:
        if payload['command'] == 'order':
            destination = payload['msg']['destination']
        elif payload['command'] == 'restart':
            pass
        else:
            logger.info('Invalid /supervisor command : {}'.format(payload['command']))
    except KeyError:
        logger.info('Invalid /supervisor message.')

def restart():
    global location_status
    logger.info('Restarting...')
    for it in SUB_TOPICS:
        client.subscribe(it[0], it[1])
    location_status = 'STARTING_POINT'
    logger.info('Restarting process completed!')

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
    for topic in SUB_TOPICS:
        client.subscribe(topic[0], topic[1])
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info('KeyboardInterrupt occured.')
        client.disconnect()
        sclient.close()
