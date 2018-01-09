
# helper function to print raw data with hex indice
# output example:
#
# Index:   0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F 
# 0000    5a a5 aa 55 5a a5 aa 55 00 00 00 00 00 00 00 00 
# 0010    00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
# 0020    60 de 00 00 28 27 6a 00 9e d8 82 bb f4 34 ea 34 
# 0030    01 00 00 00 b0 be 00 00 c7 c0 f1 15 f8 ec 4d d9 
# 0040    e4 d0 ee ba d5 e5 3a 73 7d be ed b2 fc 0a f6 64 
# 0050    92 59 7c df 03 47 7d f3 

def dump_hex_buffer(buf):
    str   = ""
    size  = len(buf)

    # print the index header in hex 0 to F
    str += "Index:\t"
    for j in xrange(0,0x10):
        str += "%2X " % j

    # print the buffer content in lines of 16 elements
    for i in range(0, size):
        # every 16 bytes we write a new line with the index
        idx = i % 16
        
        if idx == 0:
            str += "\n%04x\t" % i

        str += "%02x " %buf[i]

    return str

