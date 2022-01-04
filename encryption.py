# import the AES library
import pyaes
# Enter plain text of any byte (stream)
# i = input("Enter the plain text: ")  
# A 256 bit (32 byte) key chosen
# key = "abhijit#4387926131r513f124597851"

def encrypt(i): 
    key = "abhijit#4387926131r513f124597851"
    aes = pyaes.AESModeOfOperationCTR(str.encode(key))
# cipher text creation
    e = aes.encrypt(i)
    return e
# or, use this directly
# e = pyaes.AESModeOfOperationCTR(str.encode(key)).encrypt(i)
# d = encrypt(i)
# print("\n The Encrypted text (in bytes): \n", d)


def decrypt(e): 
# decrypting cipher text
# The counter mode of operation maintains state, so decryption requires a new instance be created
    key = "abhijit#4387926131r513f124597851"
    aes = pyaes.AESModeOfOperationCTR(str.encode(key))
    d = aes.decrypt(e)
    return d
# or, use this directly
#d = pyaes.AESModeOfOperationCTR(str.encode(key)).decrypt(e)

# print("\n The Decrypted text (in bytes): \n", decrypt(d))