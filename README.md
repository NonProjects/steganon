# SteganoN

**Steganon** is an extended implementation of the [LSB steganography algorithm](https://www.google.com/search?q=LSB+steganography+algorithm).

In short, steganography **LSB** is a method of hiding data inside pixels of image. Every pixel of an image consist of three integers (**0-255**, or **one byte**). They describe an amount of **R**ed, **G**reen and **B**lue colors. We take User's data to hide and convert it to a **bit string**; then we take next target pixel and select first integer: **R**. We convert this integer into bit string and change it's [least significant bit](https://en.wikipedia.org/wiki/Bit_numbering) to the next bit of User's data. Repeat this process for **G** and **B** then write altered pixel back into image. Repeat until User's data is not empty. Such change to **RGB** is invisible to human eye and gives us chance to hide **three bits** of data **per pixel** (three pixels per byte).

## Difference between classic LSB and LSB_WS


This repository implements a different type of LSB: **LSB With [Seed](https://en.wikipedia.org/wiki/Random_seed)** (short. `LSB_WS`). This is a (designed by [**me**](https://github.com/NotStatilko)) subclass of LSB that is use [**PRNG**](https://en.wikipedia.org/wiki/Pseudorandom_number_generator) with changeable [seed](https://en.wikipedia.org/wiki/Random_seed) to determine targeted pixels. Here, *Seed* acts like password. You must know it to extract any hidden data, and fact that image contains any hidden data is more obscure. I believe that `LSB_WS` is more strong against any [analyze](https://www.google.com/search?q=how+to+crack+lsb+stegano).

## Installation

**You can install SteganoN from PIP**
```bash
pip install steganon
```
**Or you can install with git clone**
```bash
python -m venv steganon-env
cd steganon-env && . bin/activate

git clone https://github.com/NonProjects/steganon
pip install ./steganon
```
**SteganoN has basic CLI implementation**
```bash
# Install SteganoN with CLI
pip install steganon[cli]
```

![image](https://github.com/NonProjects/steganon/assets/43419673/79e67a0a-4f4b-400d-8aa9-fdfdd9bcb7f3)


## Example

### Hiding Secret Data

```python3
from steganon import Image, LSB_WS

image = Image.open('example.png') # Open targeted Image
lsb_ws = LSB_WS(image, b'seed_0') # Init with seed=b'seed_0'

lsb_ws.hide(b'Secret!!!') # Write secret message to image pixels
image.save('example.png') # Save altered image with secret data
```
#### Under the hood (Pseudo-code)
```python
# Pseudo-code here! See source file for exact implementation

image = Image.open('example.png')

secret, seed = 'Secret!!!', b'seed_0'
secret_bin = binary(secret) = list('010100110110010101100011011100100110010101110100001000010010000100100001')

prng = PRNG(seed) # In reality we use Python's random module, which is Mersenne Twister

while secret_bin:
    # In the actual code we store position of pixels that we changed, so
    # if "random_pixel" will return us pixel that already been altered
    # we will request next position, up until we will not find empty one
    next_pixel = image.get_pixel(prng.random_pixel(image)) # (255, 0, 0)

    # Also, as there is three integers per pixel and only eight bits
    # per byte of secret data we add zero (0) to start of every bits of
    # byte of secret data so it's total size will be 9 and we can
    # easily hide whole byte of secret data in three pixels. In this
    # pseudo-code example this is ignored. 11111111 will be 011111111.

    new_pixel = []
    for color_integer in next_pixel:
        color_bits = binary(color_integer) # 255 = 11111111 (First Iteration)
        color_bits[-1] = secret_bin.pop(0) # color_bits ~= 11111110 (First Iteration)
        new_pixel.append(binary_to_int(color_bits)) # 11111110 = 254 (First Iteration)

    image.put_pixel(new_pixel) # [254, 1, 0] (After all Iterations)
```
### Extracting Secret Data
```python
# Secret Data extraction schema is pretty the same as hide process,
# the only difference is that we only take last significant byte

from steganon import Image, LSB_WS

image = Image.open('example.png') # Opening Image with hidden data
lsb_ws = LSB_WS(image, b'seed_0') # Init with seed=b'seed_0'

print(lsb_ws.extract()) # b'Secret!!!'
```

## Image Comparison

Here is comparison between [**Original image (1)**](https://github.com/NonProjects/steganon/assets/43419673/4f0f7238-f51e-45c5-80b0-3e039b26c8de) and [**Image with written on pixels data (2)**](https://github.com/NonProjects/steganon/assets/43419673/ddc67292-d085-47dc-ae04-2dd131496899).

<img src="https://github.com/NonProjects/steganon/assets/43419673/45e529b6-c45a-454c-bbf3-8426ba9dd9f5" width="777" height="-1"></img>

[**Modified Image (2)**](https://github.com/NonProjects/steganon/assets/43419673/ddc67292-d085-47dc-ae04-2dd131496899) has whole [**Zen of Python**](https://peps.python.org/pep-0020/#the-zen-of-python) written on it.\
You can extract Zen from **(2)** by using Seed `b'spam_eggs'`

## TestMode on LSB_WS

`steganon.LSB_WS` class has a `testmode` key. We can use it to check affected pixels under different seeds

<img src="https://github.com/NonProjects/steganon/assets/43419673/91d0c920-2749-4a5d-afa1-b43d76b29aa0" width="777" height="-1"></img>

## Additional Information

0. **Always use a different seed!** Pixel positions will be the same on different images and text!
1. All of this developed by me and currently **wasn't** verified by cryptography experts. Use with caution!
2. `hide()` process can be long on big Data and small image. Note: **one byte of data is 3 pixels**;
3. This library **will not** work with JPEG. PNG is OK and recommended. Other formats need testing;
4. Best template to hide data is a compressed JPEG turned to PNG. Library have `tools.pngify`, use it.

Contact me on thenonproton@pm.me (or just open Issue) if you have any feedback on this library.

## All Aboard!

Try to download [**this example image**](https://github.com/NonProjects/steganon/assets/43419673/2b13ef7c-b37f-4d4f-a88f-7b035324a905) and extract secret data from it (may take some time :)\
Seed is `b'OZZY'`, save data to the file with `.ogg` extension and play with your media player

###### Crazy? But that's how it goes!
