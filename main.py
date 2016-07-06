import machine
import ubinascii as binascii
import webrepl

from umqtt import MQTTClient

# These defaults are overwritten with the contents of /config.json by load_config()
CONFIG = {
    "broker": "192.168.1.1", # Set this to your MQTT broker IP address/hostname
    "button_pin": 0,
    "relay_pin": 12,
    "led_pin": 13,
    "client_id": b"sonoff_" +binascii.hexlify(machine.unique_id()),
    "default_on": False,
}


relay_pin = None
led_pin = None
client = None

def callback(topic, msg):
    print("Got a message!")
    if topic == topic_name(b"control"):
        if msg == b"on":
            print("Turning relay ON")
            switch_on()
            publish_state()
        elif msg == b"off":
            print("Turning relay OFF")
            switch_off()
            publish_state()
        elif msg == b"toggle":
            toggle_state()
            publish_state()
        elif msg == b"state?":
            publish_state()
        elif msg == b"webrepl":
            webrepl.start_foreground()
        else:
            print("Unknown message type, ignoring")

def switch_on():
    relay_pin.high()
    led_pin.low() # LED pin state is inverted

def switch_off():
    relay_pin.low()
    led_pin.high()

def toggle_state():
    if relay_pin.value():
        switch_off()
    else:
        switch_on()

def external_button_callback(pin):
    if relay_pin.value():
        switch_off()
    else:
        switch_on()

def publish_state():
    if relay_pin.value():
        client.publish(topic_name(b"state"), b"on")
    else:
        client.publish(topic_name(b"state"), b"off")
    print("Relay state: {}".format("on" if relay_pin.value() else "off"))

def topic_name(*args):
    parts = list(args)
    client_id = CONFIG['client_id']
    if isinstance(client_id, str):
        client_id = client_id.encode("ascii")
    parts.insert(0, client_id)
    return b"/".join(parts)

def connect_and_subscribe():
    global client
    client = MQTTClient(CONFIG['client_id'], CONFIG['broker'])
    client.set_callback(callback)
    client.connect()
    print("Connected to {}".format(CONFIG['broker']))
    topic = topic_name(b"control")
    client.subscribe(topic)
    print("Subscribed to {}".format(topic))

def setup_pins():
    global relay_pin, led_pin
    relay_pin = machine.Pin(CONFIG['relay_pin'], machine.Pin.OUT)
    led_pin = machine.Pin(CONFIG['led_pin'], machine.Pin.OUT)
    if CONFIG['default_on']:
        switch_on()
    else:
        switch_off()

def setup_button_interrupt():
    # When the button is pushed, toggle the relay state.
    button_pin = machine.Pin(CONFIG['button_pin'], machine.Pin.IN)
    button_pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=external_button_callback)

def load_config():
    import ujson as json
    try:
        with open("/config.json") as f:
            config = json.loads(f.read())
    except (OSError, ValueError):
        print("Couldn't load /config.json")
        save_config() # Might be first run, so save config.
    else:
        CONFIG.update(config)
        print("Loaded config from /config.json")

def save_config():
    import ujson as json
    try:
        with open("/config.json", "w") as f:
            f.write(json.dumps(CONFIG))
    except OSError:
        print("Couldn't save /config.json")

def setup():
    load_config()
    setup_pins()
    setup_button_interrupt()
    connect_and_subscribe()

def main_loop():
    while 1:
        client.wait_msg()

def teardown():
    try:
        client.disconnect()
        print("Disconnected.")
    except Exception:
        print("Couldn't disconnect cleanly.")

if __name__ == '__main__':
    setup()
    try:
        main_loop()
    finally:
        teardown()
