import urllib.request
import json
from datetime import datetime, timezone

def test_ingest():
    url = "http://127.0.0.1:8000/api/v1/logs"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": "payment-gateway",
        "log_level": "ERROR",
        "message": "Payment timeout error for tx_893247923847: Gateway did not respond within 5000ms"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            print(f"Status Code: {status_code}")
            print("Response Body:")
            print(json.dumps(json.loads(response_body), indent=2))
            assert status_code == 201
            print("Test Ingestion Success!")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode('utf-8'))
        raise e
    except Exception as e:
        print(f"Error: {e}")
        raise e

if __name__ == "__main__":
    test_ingest()
