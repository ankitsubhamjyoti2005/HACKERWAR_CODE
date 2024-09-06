import websocket
import json
import threading
import time

data = {
    "BeatsAvg": 0,
    "PulseRate": 0,
    "SpO2": 0,
    "BodyTemperature": 0,
}


def normalize(value, min_val, max_val):
    return (value - min_val) / (max_val - min_val)


def preprocess(data):
    processed_data = {}
    processed_data["BioImpedence"] = normalize(data["BioImpedence"], 100, 500)
    processed_data["PulseRate"] = normalize(data["PulseRate"], 40, 180)
    processed_data["SpO2"] = normalize(data["SpO2"], 70, 100)
    processed_data["BodyTemperature"] = normalize(data["BodyTemperature"], 35, 40)
    return processed_data


def analyze(processed_data):
    risk_level = 0
    if processed_data["SpO2"] < 0.9:
        risk_level += 1
    if processed_data["BodyTemperature"] > 0.8:
        risk_level += 1
    if processed_data["BioImpedence"] < 0.2:
        risk_level += 1
    if processed_data["PulseRate"] > 0.7:
        risk_level += 1

    if risk_level >= 3:
        print("Warning: High likelihood of a blood clot!")
    else:
        print("Blood clot unlikely.")

    return risk_level


def send_data_to_endpoint(processed_data, risk_level):
    endpoint = "ws://0.0.0.0:5500"
    ws = websocket.create_connection(endpoint)
    message = {
        "processed_data": processed_data,
        "risk_level": risk_level,
        "timestamp": time.time(),
    }
    ws.send(json.dumps(message))
    ws.close()


def on_message(ws, message):
    global data
    new_data = json.loads(message)

    data["BioImpedence"] = float(new_data.get("SensorData").get("bioImpedence"))
    data["PulseRate"] = float(new_data.get("SensorData").get("beatsPerMinute"))
    data["SpO2"] = float(new_data.get("SensorData").get("SpO2"))
    data["BodyTemperature"] = float(new_data.get("SensorData").get("bodyTemperature"))

    if data["SpO2"]:
        processed_data = preprocess(data)
        risk_level = analyze(processed_data)
        send_data_to_endpoint(processed_data, risk_level)


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("Connection closed")


def on_open(ws):
    print("Connection opened")


ws = websocket.WebSocketApp(
    "ws://0.0.0.0:5000",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open,
)


def run_websocket():
    ws.run_forever()


websocket_thread = threading.Thread(target=run_websocket)
websocket_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    ws.close()
    websocket_thread.join()
