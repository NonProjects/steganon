from random import Random
from typing import Callable, Optional, Generator

from PIL import Image

from .errors import (
    StateAlreadyCreated, SeedAlreadyUsed,
    InvalidSeed, TestModeEnabled, IncorrectDecode
)
__all__ = ['LSB_WS']


class LSB_WS:
    """
    This class implements an LSB-With-Seed algorithm. The
    LSB stands for a "Least Significant Bit" -- last bit
    of the multi-bit binary number. Steganography by LSB
    is working on a pixel values, which is a 3 numbers (
    the RGB). We change the last bit of each number to the
    one bit of information you want to hide, until all
    information will be encoded (hidden) in the image.

    ?: Google "Steganography LSB algorithm" for more info.
    !: We will need a three pixels to hide one byte of data.

    The "Seed" (a typical PRNG seed) will define what
    pixels will be affected, so specifying same seed
    on encoding and decoding data will result in a
    successful extraction, otherwise not.
    """
    def __init__(
            self, image: Image, seed: bytes,
            testmode: Optional[bool] = False,
            progress_callback: Optional[Callable] = None):
        """
        Arguments:
            image (``Image``):
                The target image. You will hide
                your secret text in it.

            seed (``bytes``):
                Selection of pixels will be based
                on a PRNG seed. Treat it like a
                password and DON'T disclose.

            testmode (``bool``, optional):
                Will enable TestMode if ``True``. On
                TestMode all target pixels will be
                replaced either by Red (if next bit
                of data is 0) or Green (if next bit
                of data is 1). Obviously, extract
                will not work under this mode. Use it
                to see distribution with different
                seed if you need to / interested.
        """
        self.image = image
        self._size = self.image.size
        self.__px = self.image.load()

        self.__information_pixels_pos = []
        self.__mode = 0

        # We will set pixel to "1" on coordinate that we used
        self.__edited_pixels = Image.new('1', self._size)
        self.__ep_px = self.__edited_pixels.load()

        self.__testmode = testmode
        self.__seed = seed

        self._random = Random(self.__seed)
        self._progress_callback = progress_callback

    def __get_free_pixel_position(self) -> tuple:
        """Will return coordinates of unused pixel"""
        while True:
            x = self._random.randrange(self._size[0])
            y = self._random.randrange(self._size[1])

            if self.__ep_px[x,y]:
                continue

            self.__ep_px[x,y] = 1
            return (x,y)

    def __extract_bits_from_pixel(self, pixel: tuple) -> str:
        """Will extract three hidden bits from the pixel"""
        pixel = (pixel,) if isinstance(pixel, int) else pixel
        return tuple((i & 1 for i in pixel[:3]))

    def __coordinates_to_bytes(self, coordinates: list) -> bytes:
        """Will convert a bunch of coordinates to bytes"""

        counter, byte, bytes_ = 0, 0, []
        for c in coordinates:
            bits = self.__extract_bits_from_pixel(self.__px[c[0], c[1]])

            for bit in bits:
                byte = (byte << 1) | bit

            if byte > 255:
                raise IncorrectDecode(
                    'Can not decode bytes. Maybe image was incorrectly '
                    'compressed on saving? Use bigger W:H if you want '
                   f'to store big data. Byte={byte}')
            counter += 3

            if counter == 9:
                bytes_.append(byte)
                counter, byte = 0, 0

        return bytes_

    def __get_information_size(self) -> int:
        """Will return a total length of hidden in image text"""
        if not self.__information_pixels_pos:
            self.__information_pixels_pos = [
                self.__get_free_pixel_position() for _ in range(9)]
        try:
            information_bytes = self.__coordinates_to_bytes(
                self.__information_pixels_pos)
        except ValueError as e:
            raise InvalidSeed from e

        if not information_bytes:
            return 0
        else:
            length = 0
            for byte in information_bytes:
                length = (length << 8) | byte
            return length

    @property
    def seed(self):
        """Will return specified seed"""
        return self.__seed

    @seed.setter
    def seed(self, seed):
        if self.__mode:
            raise SeedAlreadyUsed
        self.__seed = seed
        self._random = Random(self.__seed)

    def hide(self, information: bytes) -> int:
        """
        Method used to hide data in image.

        Arguments:
            information (``bytes``):
                An information you want to hide. Will
                be added to the old one.

                You can hide up to (x_size * y_size) // 3
                bytes of data. Use bigger images.

        Returns:
            A total length of hidden in image data.
        """
        if self.__mode == 2:
            raise StateAlreadyCreated('''
                Extract state is already created, can
                not write. Please make a new object'''
            )
        if not information:
            raise ValueError('information can not be empty')

        if not self.__mode:
            info_size = len(information)
            self.__mode = 1
        else:
            info_size = self.__get_information_size() + len(information)

        max_allowed_bytes = (self._size[0] * self._size[1]) // 3

        if info_size > max_allowed_bytes:
            raise OverflowError(
                '''Can not add more info. Maximum for your '''
               f'''image is a {max_allowed_bytes}, used '''
               f'''{info_size - len(information)} bytes, you '''
               f'''want to write {info_size}.'''
            )
        elif info_size > 256**3-1:
            raise OverflowError('Can not add more info, max is 256^3-1 bytes')

        info_size_bytes = int.to_bytes(info_size, 3, 'big')
        information = [*info_size_bytes, *information]
        info_pixels_pos_copy = self.__information_pixels_pos.copy()

        information_length = len(information)
        perc5, counter = int((5 / 100) * information_length), 1

        for indx, byte in enumerate(information):
            if self._progress_callback:
                # We report only progress by 5% because
                # calling progress_callback can be slow
                if indx == perc5 * counter:
                    self._progress_callback(indx+1, information_length)
                    counter += 1

            if byte == 0:
                current_bits = [0]
            else:
                current_bits = []
                while byte > 0: # Insert the LSB at the beginning
                    current_bits.insert(0, byte & 1)
                    byte >>= 1  # Shift the number right by 1

            # Should be bit per pixel color (RGB), so 8 bits per byte
            # isn't enough. We add additional zero at binary start.
            current_bits = [*((0,)*(9 - len(current_bits))), *current_bits]
            # Will take current_bits[current_bits_pos] later on code
            current_bits_pos = 0

            for _ in range(3):
                while True:
                    if info_pixels_pos_copy:
                        x,y = info_pixels_pos_copy.pop(0)
                    else:
                        x = self._random.randrange(self._size[0])
                        y = self._random.randrange(self._size[1])

                        if not self.__ep_px[x,y]:
                            break

                if len(self.__information_pixels_pos) < 9:
                    self.__information_pixels_pos.append((x,y))

                candidate_pixel = self.__px[x,y]
                self.__ep_px[x,y] = 1

                # In case of grayscale, returns int instead of tuple
                if isinstance(candidate_pixel, int):
                    candidate_pixel = (candidate_pixel,)

                if self.__testmode:
                    if current_bits[current_bits_pos] == 0:
                        new_pixel = [255,0,0]
                    else:
                        new_pixel = [0,255,0]

                    current_bits_pos += 1
                else:
                    new_pixel = []
                    for color in candidate_pixel[:3]:
                        target_bit = current_bits[current_bits_pos]

                        if color == 0:
                            color_bits = [0]
                        else:
                            color_bits = []
                            while color > 0: # Insert the LSB at the beginning
                                color_bits.insert(0, color & 1)
                                color >>= 1  # Shift the number right by 1

                        if target_bit == 0:
                            color_bits[-1] = color_bits[-1] & ~(1 << 0)
                        else:
                            color_bits[-1] = color_bits[-1] | (1 << 0)

                        byte = 0
                        for bit in color_bits:
                            byte = (byte << 1) | bit

                        new_pixel.append(byte)
                        current_bits_pos += 1

                # If image has transparency
                if len(candidate_pixel) > 3:
                    new_pixel.extend(candidate_pixel[3:])

                self.__px[x,y] = tuple(new_pixel)

        if self._progress_callback:
            self._progress_callback(information_length, information_length)

        return info_size

    def extract(self) -> bytes:
        """
        Method used to extract hidden data from the image.
        Will return all data in one call.

        For large data, consider using extractgen().
        """
        return next(self.extractgen(float('inf')))

    def extractgen(self, chunksize: Optional[int] = None)\
            -> Generator[bytes, None, None]:
        """
        Generator that you can use to extract data by chunks
        instead of one call. Useful for big hidden data, as
        loading whole information may be crazy on RAM.

        Arguments:
            chunksize (``int``, optional):
                chunksize is a size of bytes that would be returned
                from generator per one next(). Please note that
                RAM consumption wouldn't be equal to chunksize,
                as there is many data to store.

                If not specified, chunksize is 250000, or 250KB,
                which corresponds to ~270MB of RAM at max.

                Typically there is about zero increase in speed
                on bigger chunksize, so you may ignore this kwarg
                if you don't need it otherwise.
        """
        if self.__testmode:
            raise TestModeEnabled('You can\'t use extract on TestMode.')

        if self.__mode == 1:
            raise StateAlreadyCreated('''
                Write state is already created, can
                not extract. Please make a new object'''
            )
        self.__mode = 2
        info_size = self.__get_information_size()

        if not info_size:
            raise InvalidSeed

        perc5 = int((5 / 100) * info_size)
        chunksize = chunksize or 250000
        buffer, counter = [], 0

        for i in range(info_size*3): # 3 pixels per byte, so *3
            if len(buffer) >= chunksize*3:
                yield bytes(self.__coordinates_to_bytes(buffer))
                buffer.clear()

            buffer.append(self.__get_free_pixel_position())

            if self._progress_callback:
                # We report only progress by 5% because
                # calling progress_callback can be slow
                if i == perc5 * counter:
                    self._progress_callback(i+1, info_size*3)
                    counter += 1

        if self._progress_callback:
            self._progress_callback(info_size*3, info_size*3)

        if buffer:
            yield bytes(self.__coordinates_to_bytes(buffer))

    def save(self, fp, format: Optional[str] = None) -> None:
        """
        Will save image under specified format with all
        original metadata preserved. Uses the pillow
        ``self.image.save()`` under the hood.

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
