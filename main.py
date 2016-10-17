import machine
import ubinascii as binascii

from umqtt.simple import MQTTClient

from colorsys import hsv_to_rgb

# These defaults are overwritten with the contents of /config.json by load_config()
CONFIG = {
    "broker": "10.0.1.216", # Set this to your MQTT broker IP address/hostname
    "neopixel_pin": 5,
    "neopixel_count": 19,
    "client_id": b"pumpkin_" +binascii.hexlify(machine.unique_id()),
}


hue = 0.3
saturation = 0.0
brightness = 0.02
powered_on = True

strip = None
client = None

def callback(topic, msg):
    print("Got a message!")
    if topic == topic_name(b"control"):
        try:
            msg_type, payload = msg.split(b":", 1)
            if msg_type == b"h":
                set_hue(payload)
            elif msg_type == b"s":
                set_saturation(payload)
            elif msg_type == b"b":
                set_brightness(payload)
            elif msg_type == b"power":
                set_power(payload)
            else:
                print("Unknown message type, ignoring")
        except Exception:
            print("Couldn't parse/handle message, ignoring.")

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

def set_brightness(msg):
    global brightness
    brightness = max(0.0, min(100.0, int(msg))) / 100.0
    update_strip()

def set_saturation(msg):
    global saturation
    saturation = max(0.0, min(100.0, float(msg.decode("utf-8")))) / 100.0
    update_strip()

def set_hue(msg):
    global hue
    hue = max(0.0, min(360.0, float(msg.decode("utf-8")))) / 360.0
    update_strip()

def set_power(msg):
    global powered_on
    powered_on = msg == b"on"
    update_strip()

def update_strip():
    if powered_on:
        r, g, b = hsv_to_rgb(hue, saturation, brightness)
        r, g, b = int(r*255), int(g*255), int(b*255)
        strip.fill((r, g, b))
    else:
        strip.fill((0, 0, 0))
    strip.write()

def connect_and_subscribe():
    global client
    client = MQTTClient(CONFIG['client_id'], CONFIG['broker'])
    client.set_callback(callback)
    client.connect()
    print("Connected to {}".format(CONFIG['broker']))
    topic = topic_name(b"control")
    client.subscribe(topic)
    print("Subscribed to {}".format(topic))

def setup_neopixels():
    global strip
    import neopixel
    strip = neopixel.NeoPixel(machine.Pin(CONFIG['neopixel_pin']), CONFIG['neopixel_count'])
    update_strip()

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
    setup_neopixels()
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
