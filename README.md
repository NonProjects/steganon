# SteganoN

**Steganon** is an extended implementation of the [LSB Matching steganography algorithm](https://www.google.com/search?q=LSB+Matching+steganography+algorithm).

In short, steganography **LSB** is a method of hiding data inside pixels of image. Every pixel of a regular image typically consist of three integers (**0-255**, or **one byte**). They describe an amount of **R**ed, **G**reen and **B**lue colors. We take User's data to hide and convert it to a **bits**; then we take the next target pixel and select first (color channel) integer: **R**. If the last bit of color channel is the **same as our next bit** from the data bit string, **we do nothing**; **if they differ**, we **randomly add or subtract 1 from color channel**. For example, if channel is `222`, we **randomly** `+1` or `-1`, so result would be either `221` or `223`. However, **if channel is** `0` **we always** `+1`, and **if** `255` **we always** `-1`. This essentially will change the [least significant bit](https://en.wikipedia.org/wiki/Bit_numbering) of color channel (e.g **R**) to the bit we want. Repeat this process for **G** and **B** then write altered pixel back into image. Repeat on the next pixels until User's data is not empty. Such change to **RGB** is invisible to human eye and gives us chance to hide **three bits** of data **per pixel** (or, in this library, — three pixels per byte).

## Difference between classic LSB and LSB\_MWS

This repository implements a special type of LSB Matching: **LSB Matching With [Seed](https://en.wikipedia.org/wiki/Random_seed)** (short. `LSB_MWS`). This algorithm utilizes [**PRNG**](https://en.wikipedia.org/wiki/Pseudorandom_number_generator) with changeable [seed](https://en.wikipedia.org/wiki/Random_seed) to select targeted pixels. Moreover, in `LSB_MWS`, one cover Image may contain different, multiple secret Datas on different, multiple Seeds. Thus, this project supports the **Deniable Hide** feature — you can reveal as much Data as you want.

**Deniable Hide** works as a chain of Seeds. Instead of specifying only one Seed, you can pass as many as you wish and attach unique secret Data to each one of them independently. `LSB_MWS` *Hide function* will ensure that each bit of different Datas are stored in unique Pixel without overlapping. On *Extract*, to get a first hidden Data you will need to provide a Seed`(1)`, to get a second Data — Seed`(1)` & Seed`(2)`, to get a third Data — Seed`(1)`, Seed`(2)` & Seed`(3)`, and so on. There is a **zero correlations between Seeds**. In case of extortion, **you can reveal only Seed**`(1)` and criminal—or *whoever*, will **never** know that there is more hidden data deeper.

**We don't feed Seeds directly into the PRNG**, we **hash** them firstly in a special\
manner with `SHA512` **truncated to the *last* 32 bytes**.

***(Iterations on MultiSeed with three Seeds)***
1. We create *Initializator* hash by hashing a constant-*Basis* with `ImageSize` (*Width*/*Height*);
2. We hash *Initializator* with Seed`(1)` — that is our **first** PRNG Seed;
3. We hash Seed`(1)` with Seed`(2)`, — that is our **second** PRNG Seed;
4. We hash Seed`(2)` with Seed`(3)`, — that is our **third** PRNG Seed.

It means that **Seeds are dependent on each other** and *Initializator* **depends on the Image Width & Height**, thus, each unique-sized Image will utilize **different Seed values for PRNG**. This will add some protection against the brute-force or seed re-usage.

###### This can be disabled with `use_raw_seed=True` on `LSB_MWS`, though *not* recommended.

## Installation

**You can install SteganoN with PIP**
```bash
pip install steganon
```
**Or you can install it after `git clone`**
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
![steganon1.0](https://github.com/user-attachments/assets/608752c2-3cf3-4c6f-abf5-d652700f9e6a)

## Example

### (One Seed) Hiding Secret Data

```python3
from steganon import Image, LSB_MWS

image = Image.open('example.png') # Open targeted Image
lsb_mws = LSB_MWS(image, b'seed_0') # Init with seed=b'seed_0'

lsb_mws.hide(b'Secret!!!') # Write secret message to image pixels
image.save('example.png') # Save altered image with secret data
```

### (One Seed) Extracting Secret Data
```python
from steganon import Image, LSB_MWS

image = Image.open('example.png') # Open Image with hidden data
lsb_mws = LSB_MWS(image, b'seed_0') # Init with seed=b'seed_0'

print(lsb_mws.extract()) # b'Secret!!!'
```

### (MultiSeed) Hiding Secret Data

```python3
from steganon import Image, LSB_MWS

image = Image.open('example.png') # Open targeted Image
seeds = (b'seed_0', b'seed_1',  b'seed_2') # You can use as much as you want
lsb_mws = LSB_MWS(image, seeds) # Init LSB_MWS with multiple seeds

lsb_mws.hide(b'Secret data on Seed(0)!!!') # Write secret message to image pixels
lsb_mws.next() # Switch to the next Seed (b'seed_1')

lsb_mws.hide(b'Secret data on Seed(1)!!!') # Write secret message to image pixels
lsb_mws.next() # Switch to the next Seed (b'seed_2')

lsb_mws.hide(b'Secret data on Seed(2)!!!') # Write secret message to image pixels
image.save('example.png') # Save altered image with secret data
```

### (MultiSeed) Extracting Secret Data
```python
from steganon import Image, LSB_MWS

image = Image.open('example.png') # Open targeted Image
seeds = (b'seed_0', b'seed_1',  b'seed_2') # You can use as much as you want
lsb_mws = LSB_MWS(image, seeds) # Init LSB_MWS with multiple seeds

print(lsb_mws.extract()) # b'Secret data on Seed(0)!!!'
lsb_mws.next() # Switch to the next Seed (b'seed_1')
print(lsb_mws.extract()) # b'Secret data on Seed(1)!!!'
lsb_mws.next() # Switch to the next Seed (b'seed_2')
print(lsb_mws.extract()) # b'Secret data on Seed(2)!!!'
```

## Image Comparison

Here is comparison between [**Original image (1)**](https://github.com/user-attachments/assets/2d639687-718e-4868-afbb-fc431b35e747) and [**Image with written on pixels data (2)**](https://github.com/user-attachments/assets/4b3de992-2fcb-4c54-84e2-94546cd0c168).

<img src="https://github.com/user-attachments/assets/b218038d-94c6-41bc-b471-9567112e6c6e" width="777" height="-1"></img>

[**Modified Image (2)**](https://github.com/user-attachments/assets/4b3de992-2fcb-4c54-84e2-94546cd0c168) has whole [**Zen of Python**](https://peps.python.org/pep-0020/#the-zen-of-python) written on it.\
You can extract Zen from **(2)** by using Seed `b'spam_eggs'`

## TestMode on LSB\_MWS

`steganon.LSB_MWS` class has a `testmode` key. We can use it to check affected pixels under different seeds

<img src="https://github.com/user-attachments/assets/a2e1beda-f205-432e-8c2e-56dfb0d8ead7" width="777" height="-1"></img>

## Additional Information

**Tested formats:**

* ✅  **PNG**
* ✅  **BMP**
* ✅  **TIFF**
* ✅  **WEBP**
* ✅  **JPEG2000**
* ❌  **JPG**
* ❌  **HEIF**

0. This library & implementation **wasn't** verified by steganography experts. **Use with caution!**
1. **Always use a different seed!** Pixel positions `*`may be the same on different Images and Data!
2. This library **will not** work with JPEG due to its lossy design. **Use lossless formats** (e.g PNG, WEBP, etc);
3. Best `**`template to hide data is a **compressed JPEG turned to PNG**. Library has `tools.pngify`, use it;
4. The **bigger your Image**, the **bigger amount of Data you can hide** (though the less data—the `***`better).

`*  ` If Image Width/Height and Seed are the same. **Always use a unique Seed**\
`** ` Your cover Image **should** have a decent amount of "Noise" / Compression\
`***` Quite obviously, **the lower coverage**, the **less chance for analyze tools**

Contact me on **thenonproton@pm.me** (or just [**open Issue**](https://github.com/NonProjects/steganon/issues)) if you have any feedback on this library.

## All Aboard!

Try to download [**this example image**](https://github.com/user-attachments/assets/cd1e1785-fead-4a80-83c7-f3400334c756) and extract secret information from it with seed `b'OZZY'`\
Save data to the file with `.ogg` extension and play it with your favourite media player.

###### *Flying high again!*
