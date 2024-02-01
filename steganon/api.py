from random import randrange, seed as random_seed
from os import PathLike

from PIL import Image

from .errors import (
    StateAlreadyCreated, SeedAlreadyUsed,
    InvalidSeed, TestModeEnabled
)

__all__ = ['LSB_WS']

class LSB_WS:
    """
    This class implements an LSB-With-Seed algorithm. The
    LSB stands for a "Least Significant Bit" -- last bit
    of the multi-bit binary number. Steganography by LSB
    is working on a pixel values, which is a 3 numbers (
    the RGB). We change a last bit of each number to the
    one bit of information you want to hide, until all
    information will be encoded (hidden) in the image.

    ?: Google "Steganography LSB algorithm" for more info.
    !: We will need a three pixels to hide one byte of data.

    The "Seed" (a typical PRNG seed) will define what
    pixels will be affected, so specifying same seed
    on encoding and decoding data will result in a
    successful extraction, otherwise not.
    """
    def __init__(self, image: Image, seed, testmode: bool=False):
        """
        Arguments:
            image (``Image``):
                The target image. You will hide
                your secret text in it.

            seed (*Any hashable Python object*):
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
        self.__edited_pixels_pos = set()
        self.__mode = 0

        self.__testmode = testmode

        self.__seed = seed
        random_seed(self.__seed)

    def __get_free_pixel_position(self) -> tuple:
        """Will return coordinates of unused pixel"""
        while True:
            x = randrange(self._size[0])
            y = randrange(self._size[1])

            if (x,y) in self.__edited_pixels_pos:
                continue
            else:
                self.__edited_pixels_pos.add((x,y))
                return (x,y)

    def __extract_bits_from_pixel(self, pixel: tuple) -> str:
        """Will extract three hidden bits from the pixel"""
        pixel = (pixel,) if isinstance(pixel, int) else pixel
        return ''.join((bin(i)[-1] for i in pixel[:3]))

    def __coordinates_to_bytes(self, coordinates: list) -> bytes:
        """Will convert a bunch of coordinates to bytes"""
        bits = ''.join([
            self.__extract_bits_from_pixel(self.__px[i[0], i[1]])
            for i in coordinates
        ])
        bytes_ = []
        for _ in range(len(bits)//9):
            bytes_.append(bytes(
                [int(bits[:9],2)])
            )
            bits = bits[9:]

        return b''.join(bytes_)

    def __get_information_size(self) -> int:
        """Will return a total length of hidden in image text"""
        if not self.__information_pixels_pos:
            self.__information_pixels_pos = [
                self.__get_free_pixel_position() for _ in range(9)
            ]
        try:
            information_bytes = self.__coordinates_to_bytes(
                self.__information_pixels_pos
            )
        except ValueError:
            raise InvalidSeed(InvalidSeed.__doc__) from None

        if not information_bytes:
            return 0
        else:
            return int.from_bytes(information_bytes,'big')

    @property
    def seed(self):
        """Will return specified seed"""
        return self.__seed

    @seed.setter
    def seed(self, seed):
        if self.__mode:
            raise SeedAlreadyUsed('Old seed already in use, can not change')
        self.__seed = seed
        random_seed(self.__seed)

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

        information = list(information)

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

        info_size_bytes = list(int.to_bytes(info_size, 3, 'big'))
        information = [*info_size_bytes, *information]
        info_pixels_pos_copy = self.__information_pixels_pos.copy()

        while information:
            current_bits = list(bin(information.pop(0))[2:].zfill(8))
            # Should be bit per pixel color (RGB), so 8 bits per byte
            # isn't enough :D. We add additional zero at binary start
            current_bits.insert(0, '0')

            while current_bits:
                while True:
                    if info_pixels_pos_copy:
                        x,y = info_pixels_pos_copy.pop(0)
                    else:
                        x = randrange(self._size[0])
                        y = randrange(self._size[1])

                    if len(self.__information_pixels_pos) < 9\
                        and (x,y) in self.__information_pixels_pos:
                            continue
                    elif (x,y) in self.__edited_pixels_pos\
                        and (x,y) not in self.__information_pixels_pos:
                            continue
                    else:
                        if len(self.__information_pixels_pos) < 9:
                            self.__information_pixels_pos.append((x,y))

                        candidate_pixel = self.__px[x,y]
                        self.__edited_pixels_pos.add((x,y))

                        # In case of grayscale
                        if isinstance(candidate_pixel, int):
                            candidate_pixel = (candidate_pixel,)

                        if self.__testmode:
                            # This is a current bit of data to hide
                            current_bit = current_bits.pop(0)

                            if current_bit == '0':
                                new_pixel = [255,0,0]
                            else:
                                new_pixel = [0,255,0]
                        else:
                            new_pixel = []
                            for color in candidate_pixel[:3]:
                                color_bits = list(bin(color)[2:])
                                color_bits[-1] = current_bits.pop(0)
                                color_bits = ''.join(color_bits)
                                new_pixel.append(int(color_bits,2))

                        # Image with transparency
                        if len(candidate_pixel) == 4:
                            new_pixel.append(candidate_pixel[-1])

                        self.image.putpixel((x,y), tuple(new_pixel))
                        break

        return info_size

    def extract(self) -> bytes:
        """
        Method used to extract hidden data from
        the image. Will return all data by call.
        """
        if self.__testmode:
            raise TestModeEnabled('Can\'t use extract() on TestMode.')

        if self.__mode == 1:
            raise StateAlreadyCreated('''
                Write state is already created, can
                not extract. Please make a new object'''
            )
        self.__mode = 2
        random_seed(self.__seed)

        hidden_bytes = self.__coordinates_to_bytes([
            self.__get_free_pixel_position()
            for _ in range(self.__get_information_size()*3)
        ])
        return hidden_bytes

    def save(self, fp, format: str=None) -> None:
        """Sugar to the self.image.save method"""
        self.image.save(fp, format=format)
