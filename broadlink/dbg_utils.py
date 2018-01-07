
def init_buffer(size):
    buf = bytearray(size)

    for i in range(0,size):
        buf[i] = 0
        
    return buf

# helper function to print raw data
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

# Helper function prints the buffer message on screen
def format_frame(msg):
    data  = []
    str   = ""
    size  = len(msg)
    print "Package of size: %s" % size

    for i in range(0, size):
        txt = "[%2d] %2X " % (i, msg[i])
        data.append( txt )

    for i in range(0, 10):
        for j in range(0,13):
            idx = (j*10)+i
            if idx < len(msg):
                str += data[ idx ]
        str += "\n"

    if size > 37:
        print "36-37 Device ID %x%x" % (msg[37],msg[36])

    if size > 57:
        print "Plug IP: 54-57 IP %s:%s:%s:%s" %(msg[54],msg[55],msg[56],msg[57])

    return str 

