import binascii
import os


def generate():
    return binascii.hexlify(os.urandom(20)).decode()
