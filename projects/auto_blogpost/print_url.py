import test_freeimage
print("Uploaded URL:", test_freeimage.res.json().get("image", {}).get("url"))
