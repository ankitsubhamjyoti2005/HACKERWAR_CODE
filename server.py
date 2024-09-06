import asyncio
import websockets
import json
import boto3
import decimal

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("table")

last_processed_payload = None
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


async def fetch_data_from_dynamodb():
    global last_processed_payload
    try:
        response = table.scan()
        items = response["Items"]

        data = {
            "SensorData": {
                "beatsPerMinute": 0,
                "bioImpedence": 0,
                "SpO2": 0,
                "bodyTemperature": 0,
            }
        }

        if items:
            latest_item = max(items,key=lambda x: int(x.get("timestamp",0)))

            payload = latest_item.get("payload", {})

            if payload != last_processed_payload:
                last_processed_payload = payload
            data["SensorData"]["beatsPerMinute"] = json.dumps(
                payload.get("beatsPerMinute", 0), cls=DecimalEncoder
            )
            data["SensorData"]["bioImpedence"] = json.dumps(
                payload.get("bioImpedence", 0), cls=DecimalEncoder
            )
            data["SensorData"]["SpO2"] = json.dumps(
                payload.get("SpO2", 0), cls=DecimalEncoder
            )
            data["SensorData"]["bodyTemperature"] = json.dumps(
                payload.get("bodyTemperature", 0), cls=DecimalEncoder
            )

        return data
    except Exception as e:
        print(f"Error fetching data from DynamoDB: {e}")
        return {}


async def handle_client(websocket):
    while True:
        try:
            message = await websocket.recv()
            received_data = json.loads(message)
            print("Received from client:", json.dumps(received_data, indent=4))

        except websockets.exceptions.ConnectionClosed:
            pass
            # print("Connection with client closed.")

        except Exception as e:
            print(f"Error receiving data from client: {e}")
            break


async def send_data_from_dynamodb(websocket, path):
    receive_task = asyncio.create_task(handle_client(websocket))

    try:
        while True:
            data = await fetch_data_from_dynamodb()

            print("Fetched data from DynamoDB:", json.dumps(data, indent=4))

            if data:
                await websocket.send(json.dumps(data))
            else:
                print("No data to send.")

            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error sending data to client: {e}")

    finally:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass


start_server = websockets.serve(send_data_from_dynamodb, "0.0.0.0", 5000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
