import h2
import socket
import ssl
import h2.connection
import time
import sys

def determine_sent(sockhost, host, port, path):
    frames=grab_frames(sockhost, host,port, path)
    origin_sent=False
    for frame in frames:
        if frame[0]==12:
            origin_sent=True
    return origin_sent

def get_url_conn(sockhost, host , port, path, body=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((sockhost, port))
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_ctx.verify_mode=ssl.CERT_NONE
    ssl_ctx.set_npn_protocols(['h2'])
    tls=ssl_ctx.wrap_socket(s, server_hostname=host)
    conn = h2.connection.H2Connection()
    conn.initiate_connection()
    tls.sendall(conn.data_to_send())
    sid = conn.get_next_available_stream_id()
    conn.send_headers(sid, [
        ( ':method', 'GET'),
        ( ':authority', host),
        ( ':scheme', 'https'),
        ( ':path', path)])
    if body != None:
        conn.send_data(sid, body)
    conn.end_stream(sid)
    tls.sendall(conn.data_to_send())
    return (tls, conn)
    
def grab_frames(sockhost, host, port, path, body=None):
    (tls,conn)=get_url_conn(sockhost, host, port, path, body)
    done=False
    totdata=bytes()
    while not(done):
        data = tls.recv(1024)
        if not data:
            break
        totdata +=data
        events = conn.receive_data(data)
        for event in events:
            print event
            if isinstance(event, h2.events.StreamEnded):
                done=True

    totdata=memoryview(totdata)
    frames=list()
    end=len(totdata)
    curr = 0
    while curr<end:
        header=totdata[curr: curr+9].tolist()
        framelen = header[0]*2**16+header[1]*2**8+header[2]
        frametype = header[3]
        streamid = header[5]*2**24+header[6]*2**16+header[7]*2**8+header[8]
        frames.append((frametype, streamid, totdata[curr+9:curr+9+framelen].tobytes()))
        curr+=9
        curr+=framelen
    return frames

print determine_sent(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
