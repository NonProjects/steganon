from typing import (
    Callable, Optional, Union, Generator,
    List, Tuple
)
from os import urandom
from random import Random
from hashlib import sha512

from PIL import Image

from .errors import (
    StateAlreadyCreated, TestModeEnabled,
    NotSupportedImage, InvalidSeed
)
__all__ = ['LSB_MWS']


class LSB_MWS:
    """
    This class implements LSB Matching-With-Seed algorithm.
    LSB stands for the "Least Significant Bit" -- last bit
    of the multi-bit binary number. Steganography by LSB
    is working on a pixel values, which is a 3 integers (
    the RGB). We change the last bit of each number to the
    one bit of information you want to hide, until all
    information will be encoded (hidden) in the image.

    (1)
    LSB Matching differ from the popular Replacement in
    quite simple yet elegant way: in Replacement, we
    are *changing* last bit of integer to one bit of
    our information. On big write magnitudes, such
    changes may produce anomalies in pixel color
    distribution and, thus, can be analyzed with
    sepcial tools. In LSB Matching, if last bit of
    color channel is the same as information bit, we
    do nothing; otherwise we randomly add or subtract
    one (+1 or -1) from the color channel. If target
    information bit is even, plus one or minus one
    will *always* produce even number, the same is
    for odd. In a case where our add/subtract may
    "overflow" integer we always use correct
    operation, skipping random (e.g +1 for 0 and
    -1 for 255). Because of random "noise", LSB
    Matching is more resistant against raw pixel analyze.

    (2)
    This particular implementation (LSB_MWS) also uses PRNG
    (specifically, Python's Mersenne Twister) to randomly
    select pixels from Cover Image. In a nutshell, on Hide:
        -
        1. We reserve first 12 random coordinates (InfoSize
           Pixels) for the total written Information Size;

        2. We randomly write Information bits to other pixels;

        3. We write total Information size as 4-byte integer
           into the InfoSize pixels.

    After Hide, on Extract:
        1. We obtain InfoSize pixels (first 12 random coordinates);
           extract LSB from them; get Information Size;

        2. While "Information Size" amount of bytes is not
           yielded, we extract LSB from the next pixels,
           construct bytes from 8 bits, yield.

    Quite obviously, PRNG requires Seed. Here, you should treat
    Seed as Password/Secret Key that is used to Hide or Extract
    data. Under the hood in this class we hash your Seed (or
    multiple Seeds -- check next paragraph) in a special manner,
    where "Basis" depends on a hashed constant bytestring plus
    image W:H, Seed(0) depends on a Basis, Seed(1) depends on
    a Seed(0), and Seed(N) depends on a Seed(N-1). This means
    that every unique Image size (Width:Height) will have
    unique "PRNG Seed" on the same "User-specified Seed". Re-
    using Seed is generally NOT recommended, but this should
    protect Image with data slightly more from bruteforce.

    (3)
    This implementation also supports MultiSeed mode, which You
    can use to write a Deniable Hide into your Image. Each next
    Seed will have it's own Data, and you can reveal as much
    as you want. For example, if the next Hide was used:

    .. code-block:: python

            from steganon import Image, LSB_MWS

            image = Image.open('image.png')
            seed = (b'Seed1', b'Seed2')
            lsb_mws = LSB_MWS(image, seed)

            lsb_mws.hide(b'This is a *very* secret message!')
            lsb_mws.next() # Use .next() to switch to next Seed

            lsb_mws.hide(b'Actual secret data.')
            lsb_mws.save('image-h.png')

    Then, on Extract, you can reveal only "Seed1", which will
    return deniable data attached *only* to first seed. There
    will be zero evidence that your Image contains more data
    (except if Original and Altered Image would be compared
    on a pixel level. You should NEVER keep Original cover)

    .. code-block:: python

            from steganon import Image, LSB_MWS

            image, seed = Image.open('image-h.png'), b'Seed1'
            lsb_mws = LSB_MWS(image, seed)

            print(lsb_mws.extract()) # b'This is a *very* secret message!'

    To extract *both* Datas, you will need to provide First and
    Second seed (in other words: to extract Data on Seed N you
    will be required to enter all preceding Seeds), for example:

    .. code-block:: python

            from steganon import Image, LSB_MWS

            image = Image.open('image.png')
            seed = (b'Seed1', b'Seed2')
            lsb_mws = LSB_MWS(image, seed)

            print(lsb_mws.extract()) # b'This is a *very* secret message!'

            lsb_mws.next() # Again, use .next() to switch to next Seed
            print(lsb_mws.extract()) # b'Actual secret data.'

    MultiSeed is not limited to just a pair of
    Seeds, you can use as many as you wish.

    (4)
    Maximum amount of Data you can fit into Image is calculated
    by "(img_w * img_h) // 3", as we *roughly* assume that each
    byte "equals" to three pixels. This make sense because the
    more data, the slower Hide & Extract process becomes. You
    should never reach a limit.
    """
    def __init__(
            self,
            image: Image,
            seed: Union[bytes, List[bytes], Tuple[bytes, ...]],
            testmode: Optional[bool] = False,
            progress_callback: Optional[Callable] = None,
            use_raw_seed: Optional[bool] = False):
        """
        Arguments:
            image (``Image``):
                The target Image. You will hide
                your secret text in it.

            seed (``Union[bytes, List[bytes], Tuple[bytes, ...]]``):
                Seed or Seed sequence for PRNG. Will be
                used to select pixels. Treat it like a
                password and DO NOT DISCLOSE THEM.

            testmode (``bool``, optional):
                Will enable TestMode if ``True``. On
                TestMode all target pixels will be
                replaced by one of the next colors:

                - Red (0 bits changed in Pixel)
                - Green (1 bit changed in Pixel)
                - Blue (2 bits changed in Pixel)
                - Yellow (3 bits changed in Pixel)

                Obviously, extract will not work under
                this mode. Use it to see distribution with
                different Seed if you need to or interested.

            progress_callback (``Callable``, optional):
                Function which we will call to report progress
                of hide/extract. Must accept three arguments:
                current, total, seed_indx; where: "current" is
                current progress as int, "total" is a total
                progress as int, and "seed_indx" is index
                of ``seed`` (if multiple specified as seed=).

            use_raw_seed (``bool``, optional):
                We process specified Seed(s) in a special
                way before actually using them. If you
                want to use Seeds-as-specified, you can set
                this kwarg to ``True``.

                THIS IS NOT RECOMMENDED! Ignore this
                kwarg unless you have a reason not to.
        """
        self.image = image
        self._size = self.image.size
        self.__px = self.image.load()

        zz = self.__px[0,0] # zz is Zero/Zero, bbp is Bytes per pixel
        self._bbp = 1 if isinstance(zz, int) else len(zz)

        if self._bbp < 3:
            raise NotSupportedImage(
                'SteganoN supports only images with 3 or more bytes '
               f'per pixel. You\'re trying to use {self._bbp} byte '
                'Image mode. Consider RGB.')

        self.__information_pixels_pos = []
        self.__mode = 0 # 1 is hide, 2 is extract

        # We will set pixel to "1" on coordinate that we used
        self.__edited_pixels = Image.new('1', self._size)
        self.__ep_px = self.__edited_pixels.load()

        self.__testmode = testmode
        self._use_raw_seed = use_raw_seed

        if self._use_raw_seed:
            # If use_raw_seed=True, we use specified Seed/Sequence as-is.
            self.__seed = seed if isinstance(seed, (list, tuple)) else (seed,)
        else:
            # -- Construct Seeds ------------------------------------------- #
            seed = seed if isinstance(seed, (list, tuple)) else (seed,)

            # We will mix Image Size to the Seed chain "Basis" to
            # produce unique Seeds per each unique Image Size.
            img_size_bytes = int.to_bytes(self._size[0], 16, 'big')\
                + int.to_bytes(self._size[1], 16, 'big')

            # We will use this as Initializator for our seeds.
            basis = '007C7C7C2047756974617220536F6C6F2030333A33302D30353A3133207C7C7C'
            initializator = sha512(bytes.fromhex(basis) + img_size_bytes).digest()

            self.__seed = [initializator] # We will eject initializator at the end
            for s in seed:
                seed_h = sha512(sha512(s).digest() + self.__seed[-1])
                self.__seed.append(seed_h.digest()[32:])

            self.__seed.pop(0) # We don't need initializator in our seeds
            # -------------------------------------------------------------- #
        self.__current_seed = 0

        self.__written_info_size = 0 # Per seed
        self.__total_written_info_size = 0 # Total

        self.__random = Random(self.__seed[self.__current_seed])
        self._progress_callback = progress_callback

        self.__hide_stopped_on = None
        self.__finalized = False

        # Extracted InfoSize (per Seed) will be stored here
        self.__exgen_info_size = None

        # We will use it only for LSB Matching, i.e
        # deciding if add or subtract from color
        self._true_random = Random(urandom(32))

    @property
    def seed(self):
        """Will return current seed"""
        return self.__seed[self.__current_seed]

    @property
    def current_seed_pos(self):
        """Will return current seed as position"""
        return self.__current_seed

    @property
    def max_allowed_bytes(self):
        """
        Will return max amount of bytes that
        you can write into this Image
        """
        return (self._size[0] * self._size[1]) // 3

    @property
    def total_written(self):
        """Will return current seed"""
        return self.__total_written_info_size

    def hide(self, information: bytes, *, _finalize: bool=False) -> int:
        """
        Method for hiding secret Data in Image.

        You can use multiple ``.hide()`` per one LSB_MWS
        instance to write data in chunks. This is the same
        as writing all Data in one call.

        You should call ``.next()`` per each Seed if
        multiple was specified on LSB_MWS creation.

        1. Init LSB_MWS with ``(b'Seed1', b'Seed2')``
        2. Write all data you wish to access with ``Seed1``
        3. Call ``.next()`` on LSB_MWS instance
        4. Write all data you wish to access with ``Seed2``
        5. Save Image.

        Check ``LSB_MWS`` docstring for example.

        Arguments:
            information (``bytes``):
                An information you want to hide. You can hide
                up to ``self.max_allowed_bytes`` bytes. Use bigger
                Images if you need to write more Data.

            _finalize (``bool``, optional):
                Internal kwarg. Don't touch it unless you
                want to break your class instance. YOLO.

        Returns:
            A total length of hidden in Image data per Seed.
        """
        if self.__mode == 2:
            raise StateAlreadyCreated('''
                Extract state is already created, can
                not write. Please make a new object'''
            )
        if not information and not _finalize:
            raise ValueError('information can not be empty')

        if self.__finalized:
            raise StateAlreadyCreated('LSB_MWS was already finalized.')

        if not self.__mode:
            self.__mode = 1

        if not _finalize:
            self.__written_info_size += len(information)
            self.__total_written_info_size += len(information)

            if self.__total_written_info_size > self.max_allowed_bytes:
                raise OverflowError(
                    '''Can not add more info. Maximum for your '''
                   f'''image is a {self.max_allowed_bytes}, used '''
                   f'''{self.__total_written_info_size - len(information)} bytes, '''
                   f'''you want to write {self.__total_written_info_size}.'''
                )
            elif self.__total_written_info_size > 256**4-1:
                raise OverflowError('Can not add more info, max is 256^4-1 bytes')

        if _finalize:
            information = int.to_bytes(self.__written_info_size, 4, 'big')
            self.__hide_stopped_on = None

        info_pixels_pos_copy = self.__information_pixels_pos.copy()

        information_length = len(information)
        perc5, counter = int((5 / 100) * information_length), 1

        buffer, buffer_pos, info_pos = [], 0, 0
        while True:
            if not len(buffer) - (buffer_pos+1) >= 8:
                bytesc = information[info_pos:info_pos+3]
                info_pos += 3

                if self._progress_callback:
                    # We report only progress by 5% because
                    # calling progress_callback can be slow
                    if info_pos+1 >= perc5 * counter:
                        self._progress_callback(min(info_pos, information_length),
                            information_length, self.__current_seed)
                        counter += 1

                for byte in bytesc:
                    if byte == 0:
                        current_bits = [0]
                    else:
                        current_bits = []
                        while byte > 0: # Insert the LSB at the beginning
                            current_bits.insert(0, byte & 1)
                            byte >>= 1  # Shift the number right by 1

                    current_bits = [*((0,)*(8 - len(current_bits))), *current_bits]
                    buffer.extend(current_bits)

            if info_pos and not buffer:
                break

            for _ in range(3):
                if not buffer:
                    break # propagate break higher

                while True:
                    if _finalize and info_pixels_pos_copy:
                        x,y = info_pixels_pos_copy.pop(0)
                        break
                    else:
                        if self.__hide_stopped_on:
                            x,y = self.__hide_stopped_on[0]
                            candidate_pixel = self.__hide_stopped_on[1][:3]
                            break

                        x = self.__random.randrange(self._size[0])
                        y = self.__random.randrange(self._size[1])

                        if not self.__ep_px[x,y]:
                            # We store info size in 4 bytes, 1 byte is 3 pixels,
                            # so 4(bytes) * 3(pixels). Cache info len pixels.
                            if len(self.__information_pixels_pos) < 4*3:
                                self.__information_pixels_pos.append((x,y))
                                self.__ep_px[x,y] = 1
                                continue
                            break

                if _finalize or not self.__hide_stopped_on:
                    candidate_pixel = self.__px[x,y]
                    self.__ep_px[x,y] = 1

                if self.__testmode:
                    changed_bits = 0
                    for color in candidate_pixel[:3]:
                        if buffer and buffer_pos+1 > len(buffer):
                            buffer.clear() # We don't need to track anything special
                            break # like self.__hide_stopped_on on TestMode.

                        target_bit = buffer[buffer_pos]
                        if target_bit != color & 1:
                            changed_bits += 1

                        buffer_pos += 1

                    if changed_bits == 0: # If zero bits changed in Pixel,
                        new_pixel = [255,0,0] # color is Red.

                    elif changed_bits == 1: # If one bit changed in Pixel,
                        new_pixel = [0,255,0] # color is Green

                    elif changed_bits == 2: # If two bits changed in Pixel,
                        new_pixel = [0,0,255] # color is Blue

                    elif changed_bits == 3: # If three bits changed in Pixel,
                        new_pixel = [255,255,0] # color is Yellow
                else:
                    if self.__hide_stopped_on:
                        new_pixel = self.__hide_stopped_on[2]
                        candidate_pixel = candidate_pixel[len(new_pixel):]
                    else:
                        new_pixel = []

                    for color in candidate_pixel[:3]:
                        if buffer and buffer_pos+1 > len(buffer):
                            # We will use this only if multiple .hide()
                            # methods used on one object for continuous
                            # bitstream (as there is 8 bits per byte but
                            # only 3 integers per pixel, one or more
                            # color channels will be always empty.
                            self.__hide_stopped_on = (
                                (x,y), candidate_pixel, new_pixel.copy()
                            )
                            buffer.clear()
                            candidate = candidate_pixel[:3]
                            new_pixel.extend(candidate[len(new_pixel):])
                            break

                        target_bit = buffer[buffer_pos]

                        if color == 0:
                            color_bits = [0]
                        else:
                            color_shft = color

                            color_bits = []
                            while color_shft > 0: # Insert the LSB at the beginning
                                color_bits.insert(0, color_shft & 1)
                                color_shft >>= 1  # Shift the number right by 1

                        if target_bit != color_bits[-1]:
                            # We use technique called LSB Matching instead of LSB
                            # Replacement. In short, if bit we want to hide is
                            # the same as LSB of color channel, we do nothing;
                            # otherwise we randomly add or subtract 1 from
                            # the color channel. If channel is 0 and random
                            # tell us to subtract, we always add instead,
                            # same is for 255, we always subtract. See
                            # daniellerch.me/image-stego-lsbm/#1-lsb-matching
                            modifier = 1 if self._true_random.getrandbits(1) else -1

                            if modifier > 0 and color == 255:
                                modifier = -1 # Byte range is 0-255, not 256

                            elif modifier < 0 and color == 0:
                                modifier = 1 # Byte range is 0-255, not -1

                            new_pixel.append(color + modifier)
                        else:
                            new_pixel.append(color)

                        buffer_pos += 1

                # We don't work on transparency, so if hide
                # stopped on pixel that have it, then we need
                # to manually add it from original candidate_pixel,
                # which is self.__hide_stopped_on[1].
                if buffer and self.__hide_stopped_on:
                    if len(self.__hide_stopped_on[1]) > 3:
                        new_pixel.extend(self.__hide_stopped_on[1][3:])
                    self.__hide_stopped_on = None
                else:
                    # If image has transparency
                    if len(candidate_pixel) > 3:
                        new_pixel.extend(candidate_pixel[3:])

                self.__px[x,y] = tuple(new_pixel)

            if len(buffer) >= 4096: # Free some RAM
                del buffer[:buffer_pos]
                buffer_pos = 0

        if self._progress_callback:
            self._progress_callback(information_length,
                information_length, self.__current_seed)

        return self.__written_info_size

    def extract_infosize(self):
        """
        Will return amount of bytes written on Image
        """
        if self.__mode == 1:
            raise StateAlreadyCreated('''
                Write state is already created, can
                not extract. Please make a new object'''
            )
        return self.__exgen_info_size or\
            next(self.extractgen(_return_infosize_only=True))

    def extract(self) -> bytes:
        """
        Method that is used to extract hidden data
        from the image. Will return all data in one call.

        For large data consider using ``extractgen()``,
        otherwise RAM consumption may go nuts.
        """
        data = b''
        for chunk in self.extractgen():
            data += chunk
        return data

    def extractgen(self, chunksize: Optional[int] = None,
            _return_infosize_only: Optional[bool] = False)\
            -> Generator[bytes, None, None]:
        """
        Generator that you can use to extract data by chunks
        instead of one call. Useful for big hidden data, as
        loading whole information may be crazy on RAM.

        Arguments:
            chunksize (``int``, optional):
                chunksize is a size of bytes that would be yielded
                from generator per one iteration. Please note that
                RAM consumption wouldn't be equal to chunksize,
                as there is many data to store.

                If not specified, chunksize is 250000, or 250KB,
                which corresponds to ~270MB of RAM at max.

                Typically there is about zero increase in speed
                on bigger chunksize, so you may ignore this kwarg
                unless you have a reason not to.

            _return_infosize_only (``bool``, optional):
                This is internal kwarg. Will return only Information
                Size as integer if specified.
        """
        if self.__testmode:
            raise TestModeEnabled('You can\'t use extract on TestMode.')

        if self.__mode == 1:
            raise StateAlreadyCreated('''
                Write state is already created, can
                not extract. Please make a new object'''
            )
        self.__mode = 2

        if self.__exgen_info_size is not None:
            if _return_infosize_only:
                yield self.__exgen_info_size
                return

            if self.__exgen_info_size > self.max_allowed_bytes:
                raise InvalidSeed(
                     'Incorrect Seed! Max capacity of your Image is '
                    f'{self.max_allowed_bytes}, but we extracted '
                    f'InfoSize={self.__exgen_info_size}')

            info_sizeb = self.__exgen_info_size*8 # We track info_size in bit size
        else:
            info_sizeb = 0 # We track info_size in bit size

        processedb = 0 # Amount of bits we processed

        pixel_buffer = [] # Here we will store cycle pixels for exract
        pixel_buffer_pos = 0 # Position into the pixel_buffer

        chunksize = chunksize or 250000 # Approx how many pixels will be cached
        chunksizeb = chunksize*8 # How many bits we can fit into chunksize

        bits_buffer = [] # Here we will store extracted bits. This list
        bits_buffer_pos = 0 # Would be cleared if len > 4096.

        bytes_buffer = [] # Buffer for constructed bytes from bits

        counter = 1 # Multiplication counter (for progress_callback)
        perc5 = None # Will be 5% of hidden data as int (for progress_callback)

        while True:
            conditions = ( # See end of func for "(chunksizeb // 3) + 1" explanation
                len(pixel_buffer) == (chunksizeb // 3) + 1 or\
                (info_sizeb and processedb >= info_sizeb)
            )
            if conditions:
                while True:
                    if not len(bits_buffer) - (bits_buffer_pos+1) >= 8:
                        for _ in range(3):
                            bits = (i & 1 for i in pixel_buffer[pixel_buffer_pos][:3])
                            bits_buffer.extend(tuple(bits))
                            pixel_buffer_pos += 1

                    if not bits_buffer:
                        bits_buffer_pos = 0
                        break

                    byte = 0
                    for bit in bits_buffer[bits_buffer_pos:bits_buffer_pos+8]:
                        byte = (byte << 1) | bit

                    bytes_buffer.append(byte)
                    bits_buffer_pos += 8
                    processedb += 8

                    if len(bits_buffer) >= 4096:
                        del bits_buffer[:bits_buffer_pos] # free some RAM
                        bits_buffer_pos = 0

                    if self._progress_callback:
                        # We report only progress by 5% because
                        # calling progress_callback can be slow
                        if processedb == perc5 * counter:
                            self._progress_callback(processedb, info_sizeb,
                                self.__current_seed)
                            counter += 1

                    if processedb >= info_sizeb:
                        break

                    # pixel_buffer always should have at least three spare
                    # pixels for next cycle to construct 8 bits from it,
                    # thus, here we add +3 in check.
                    if pixel_buffer_pos+3 > len(pixel_buffer):
                        break

                # exit from while, we can clean pixel_buffer
                del pixel_buffer[:pixel_buffer_pos]
                pixel_buffer_pos = 0

                yield bytes(bytes_buffer)
                bytes_buffer.clear()

                if processedb >= info_sizeb:
                    if self._progress_callback:
                        self._progress_callback(info_sizeb, info_sizeb,
                            self.__current_seed)
                    return

            if not info_sizeb:
                # We store info size in 4 bytes, 1 byte is 3 pixels,
                # so 4(bytes) * 3(pixels)
                for _ in range(4*3):
                    while True:
                        x = self.__random.randrange(self._size[0])
                        y = self.__random.randrange(self._size[1])

                        if self.__ep_px[x,y]:
                            continue
                        self.__ep_px[x,y] = 1
                        break

                    pixel_buffer.append(self.__px[x,y])

                for p in pixel_buffer:
                    bits = (i & 1 for i in p[:3])
                    bits_buffer.extend(tuple(bits))

                for _ in range(4):
                    byte = 0
                    for bit in bits_buffer[:8]:
                        byte = (byte << 1) | bit

                    bytes_buffer.append(byte)
                    del bits_buffer[:8]

                for byte in bytes_buffer:
                    info_sizeb = (info_sizeb << 8) | byte

                self.__exgen_info_size = info_sizeb

                if _return_infosize_only:
                    yield self.__exgen_info_size
                    return

                if info_sizeb > self.max_allowed_bytes:
                    raise InvalidSeed(
                         'Incorrect Seed! Max capacity of your Image is '
                        f'{self.max_allowed_bytes}, but we extracted '
                        f'InfoSize={info_sizeb}')

                info_sizeb *= 8

                perc5 = int((5 / 100) * info_sizeb)
                perc5 = (perc5 >> 3) * 8 # make perc5 divisible by 8

                bits_buffer.clear()
                bytes_buffer.clear()
                pixel_buffer.clear()
            else:
                if chunksizeb > info_sizeb:
                    chunksizeb = info_sizeb
                    chunksize = chunksizeb >> 3 # >> 3 is a fast division by 8

                elif (info_sizeb - processedb) < chunksizeb:
                    chunksizeb = (info_sizeb - processedb)
                    chunksize = chunksizeb >> 3

                # As each pixel can only fit 3 bits but one byte is 8 bits,
                # we can't request/cache chunksize directly, as there would
                # be many extra pixels that (1) we can't use and (2) will
                # break our "Deniable hide" feature, as some extra pixels
                # from the Seed #0 may overlap pixels from the Seed #1.
                # To get exact amount of pixels that we need to request,
                # we need to calculate chunksizeb (how many actual bits
                # we can fit into the chunksize), then divide it by 3
                # (color channels amount, as we work only on RGB, -- 3),
                # trash out the reminder and add 1. Result is a total
                # amount of pixels that we need to request per cycle.
                total = (chunksizeb // 3) + 1

                while not len(pixel_buffer) >= total:
                    x = self.__random.randrange(self._size[0])
                    y = self.__random.randrange(self._size[1])

                    if self.__ep_px[x,y]:
                        continue
                    self.__ep_px[x,y] = 1
                    pixel_buffer.append(self.__px[x,y])

    def next(self) -> None:
        """
        Method that you should call to switch to the next Seed
        (if multiple was specified on LSB_MWS initialization).
        """
        if self.__current_seed+1 == len(self.__seed):
            raise StateAlreadyCreated('You already used all Seeds')

        if not self.__finalized and self.__information_pixels_pos:
            self.finalize()

        self.__current_seed += 1
        self.__finalized = False
        self.__hide_stopped_on = None
        self.__exgen_info_size = None
        self.__written_info_size = 0
        self.__information_pixels_pos.clear()
        self.__random = Random(self.__seed[self.__current_seed])

    def finalize(self) -> None:
        """
        This method should be called after all Data-per-Seed
        was written to the Image. Typically it will be called
        automatically on ``.next()`` or on ``.save()``, so
        you may not use it directly.
        """
        if not self.__finalized:
            self.hide(None, _finalize=True)
        self.__finalized = True

    def save(self, fp, format: Optional[str] = None) -> None:
        """
        Will save image under specified format with as much
        original metadata preserved as possible. Uses the
        pillow ``self.image.save()`` under the hood.

        You are recommended to additionally use "exiftool"
        program to mirror *all* metadata from original
        Image to Hidden if it's installed on your system.

        exiftool -TagsFromFile original.png -all:all\
            -overwrite_original hidden.png

        Arguments:
            fp:
                Target for self.image.save(fp). Can be
                file path or File-like object.

            format (``str``, optional):
                Format of Image. Please note that we
                support only lossless format, e.g PNG,
                BMP, WEBP, etc. Otherwise behaviour on
                extract process is **not defined**.
        """
        if not self.__finalized and self.__information_pixels_pos:
            self.finalize()

        format = format or self.image.format

        kwargs = {} # Unfortunately, pillow doesn't handle Metadata copying,
        for field in ('exif', 'icc_profile'): # so we copy at least what possible
            if field in self.image.info:
                kwargs[field] = self.image.info[field]

        if format.lower() == 'webp':
            self.image.save(fp, format=format, lossless=True, **kwargs)

        elif format.lower() == 'jpeg2000':
            self.image.save(fp, format=format, quality_mode='lossless', **kwargs)

        elif format.lower() == 'tiff':
            self.image.save(fp, format=format, compression='none', **kwargs)
        else:
            # PNG & BMP is always lossless formats, thus we don't need flags
            self.image.save(fp, format=format, **kwargs)
