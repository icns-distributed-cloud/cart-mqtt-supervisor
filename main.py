import json
import random
import serial
import threading
import paho.mqtt.client as mqtt

DESTINATION = '427'
sclient = None
exit_thread = False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('MQTT Connected Successfully')
    else:
        print('MQTT Connection Failed!')
        
def on_message(client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        print(data)
        
        code = 0
        if msg.topic == '/beverage/location':
            code = handle_beverage(loc=data['location'], error_padding=5)
        elif msg.topic == '/room':
            code = handle_room(label=data['label'])
        elif msg.topic == '/qr':
            code = handle_qr()
        else:
            return
        print('code:', code)
        
        if code == 3:
            client.unsubscribe('/beverage/location')
        elif code == 4:
            client.unsubscribe('/room')
        
def handle_beverage(loc, center=320, error_padding=10):
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

def read_serial(ser):
    global exit_thread
    
    line = []
    print('read_serial Thread started.')
    while True:
        print('a')
        if exit_thread:
            print('now breaking the loop of read_serial Thread')
            break
        #for c in ser.read():
            #print(c)
        print(ser.read(4))

if __name__ == '__main__':
    # Serial Connection
    sclient = serial.Serial(port='/dev/ttyS0', baudrate=115200, timeout=100)
    if not sclient.isOpen():
        print('Cannot open the serial port.')
    #thr = threading.Thread(target=read_serial, args=(sclient,))
    #thr.start()
    
    # MQTT Connection
    client_id = f'python-mqtt-{random.randint(0, 1000)}'
    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect('localhost', 1883)


    # MQTT Loop
    client.subscribe('/beverage/location', 1)
    client.subscribe('/room', 1)
    client.subscribe('/qr', 1)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print('KeyboardInterrupt occured.')
        client.disconnect()
        exit_thread = True
        sclient.close()
        #thr.join()
