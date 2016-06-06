import base64

from Crypto import Random, Util, Cipher


class Encryption:
    """
    Class that handles simple encryption using AES256.
    """
    def __init__(self):
        pass

    @staticmethod
    def encrypt(key, content):
        """
        Encrypts a given content string using the given key and a random IV.
        :param key: The key.
        :type key: str
        :param content: The content to encrypt.
        :type content: str
        :return: A base64 encoded encrypted string.
        :rtype: str
        """
        iv = Random.new().read(Cipher.AES.block_size)
        ctr = Util.Counter.new(128,
                               initial_value=long(iv.encode("hex"), 16))
        cipher = Cipher.AES.new(key, Cipher.AES.MODE_CTR, counter=ctr)
        return base64.b64encode(iv + cipher.encrypt(content))

    @staticmethod
    def decrypt(key, encrypted):
        """
        Decrypts a given encrypted string using the provided key.

        :param key: The key.
        :type key: str
        :param encrypted: The content to decrypt. Must contain the IV in
        the first 16 characters.
        :type encrypted: str
        :return: A string (empty on failure).
        :rtype: str
        """
        try:
            encrypted = base64.b64decode(encrypted)
            iv = encrypted[:16]
            ctr = Util.Counter.new(128,
                                   initial_value=long(iv.encode("hex"), 16))
            cipher = Cipher.AES.new(key, Cipher.AES.MODE_CTR, counter=ctr)
            return cipher.decrypt(encrypted[16:])
        except BaseException:
            return ""
