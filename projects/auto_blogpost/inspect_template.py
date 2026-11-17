from PIL import Image
im = Image.open('/home/ubuntu/auto_blogpost/thumb_template.png')
print("Template size:", im.size)
# check color at various coordinates
print("Color at 0, 50 (top):", im.getpixel((0, 50)))
print("Color at 0, 200 (green bar):", im.getpixel((0, 200)))
print("Color at 0, 500 (middle):", im.getpixel((0, 500)))
print("Color at 0, 950 (bottom):", im.getpixel((0, 950)))
print("Color at 1599, 1065 (bottom right):", im.getpixel((1599, 1065)))
