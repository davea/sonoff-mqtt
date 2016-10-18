import machine
import ubinascii as binascii

from umqtt.simple import MQTTClient

from config import broker

machine_id = binascii.hexlify(machine.unique_id())
print(b"Machine ID: {}".format(machine_id))

hue = 0.0
saturation = 0.0
brightness = 0.0
powered_on = False

strip = None
client = None

def callback(topic, msg):
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
    elif topic == topic_name(b"config"):
        load_config(msg)

def publish_state():
    if relay_pin.value():
        client.publish(topic_name(b"state"), b"on")
    else:
        client.publish(topic_name(b"state"), b"off")
    print("Relay state: {}".format("on" if relay_pin.value() else "off"))

def topic_name(topic):
    return b"/".join([b"light", machine_id, topic])

def set_brightness(msg):
    global brightness
    brightness = max(0.0, min(100.0, int(msg))) / 100.0
    update_strip()

def set_saturation(msg):
    global saturation
    msg = msg.decode("utf-8") if isinstance(msg, bytes) else msg
    saturation = max(0.0, min(100.0, float(msg))) / 100.0
    update_strip()

def set_hue(msg):
    global hue
    msg = msg.decode("utf-8") if isinstance(msg, bytes) else msg
    hue = max(0.0, min(360.0, float(msg))) / 360.0
    update_strip()

def set_power(msg):
    global powered_on
    msg = msg.decode("utf-8") if isinstance(msg, bytes) else msg
    powered_on = msg == "on"
    update_strip()

def update_strip():
    if strip is None:
        print("Strip hasn't been configured yet, can't update.")
        return
    if powered_on:
        r, g, b = hsv_to_rgb(hue, saturation, brightness)
        r, g, b = int(r*255), int(g*255), int(b*255)
        strip.fill((r, g, b))
    else:
        strip.fill((0, 0, 0))
    strip.write()

def connect_and_subscribe():
    global client
    client = MQTTClient(machine_id, broker)
    client.set_callback(callback)
    client.connect()
    print("Connected to {}".format(broker))
    for topic in (b'config', b'control'):
        t = topic_name(topic)
        client.subscribe(t)
        print("Subscribed to {}".format(t))

def setup_neopixels(pin, count):
    global strip
    import neopixel
    strip = neopixel.NeoPixel(machine.Pin(pin), count)
    update_strip()

def load_config(msg):
    import ujson as json
    try:
        config = json.loads(msg)
    except (OSError, ValueError):
        print("Couldn't load config from JSON, bailing out.")
    else:
        set_hue(config['hue'])
        set_saturation(config['saturation'])
        set_brightness(config['brightness'])
        set_power(config['power'])
        setup_neopixels(config['gpio_pin'], config['led_count'])

def setup():
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

def hsv_to_rgb(h, s, v):
    if s == 0.0:
        return v, v, v
    i = int(h*6.0)
    f = (h*6.0) - i
    p = v*(1.0 - s)
    q = v*(1.0 - s*f)
    t = v*(1.0 - s*(1.0-f))
    i = i%6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q

if __name__ == '__main__':
    setup()
    try:
        main_loop()
    finally:
        teardown()
