import requests

with open("/home/ubuntu/auto_blogpost/thumb-size.png", "rb") as f:
    res = requests.post(
        "https://freeimage.host/api/1/upload",
        data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload"},
        files={"source": f},
        timeout=20
    )
print("Status code:", res.status_code)
print("Response:", res.text[:300])
