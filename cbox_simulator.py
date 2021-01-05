import socket

 

localIP     = "192.168.1.166"

localPort   = 54549

bufferSize  = 1024

 

msgFromServer       = '{"INFO":{"RSP":"OK","CMD":"DISCOVERY","TS":1609717971},"SUCCESS":true,"DATA":{"GWDEVICE":"wlan0","NOMINALPWR":0,"WMAC":"40:F3:85:70:99:98","plzbridge":"2.2.1 2019-01-03 16:10:07","WMODE":"sta","FAN2MODE":1,"MOD":0,"EGW":"0.0.0.0","MAC":"40:F3:85:70:99:98","AUTONOMYTYPE":1,"ECBL":"down","WADR":"192.168.1.1","CLOUD_ENABLED":true,"EPR":"dhcp","PELLETTYPE":0,"WCH":"11","WBCST":"192.168.1.255","SYSTEM":"2.3.1 2019-01-04 16:54:29 (94a1466)","sendmsg":"2.1.2 2018-03-28 10:19:09","STOVETYPE":1,"LABEL":"Simulated CBox","EMSK":"0.0.0.0","CONFIG":0,"WGW":"192.168.1.254","SPLMIN":0,"EMAC":"40:F3:85:70:99:98","MAINTPROBE":0,"ICONN":1,"EBCST":"","WMSK":"255.255.255.0","WPWR":"-48 dBm","WPR":"dhcp","CHRONOTYPE":5,"FLUID":1,"MBTYPE":0,"WENC":"psk2","CBTYPE":"miniembplug","EADR":"0.0.0.0","FWDATE":"0-00-00","WSSID":"My_Wifi","UICONFIG":0,"GATEWAY":"192.168.1.254","SN":"FF0000000000000000SIMULATOR","APLCONN":1,"DNS":["192.168.1.254","192.168.1.254","127.0.0.1"],"FAN2TYPE":1,"VER":0,"SPLMAX":255}}'

bytesToSend         = str.encode(msgFromServer)

 

# Create a datagram socket

UDPServerSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

# Bind to address and ip

#UDPServerSocket.bind((localIP, localPort))
UDPServerSocket.bind(("", localPort))

 

print("UDP server up and listening")

 

# Listen for incoming datagrams

while(True):

    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)

    message = bytesAddressPair[0]

    address = bytesAddressPair[1]

    clientMsg = "Message from Client:{}".format(message)
    clientIP  = "Client IP Address:{}".format(address)
    
    print(clientMsg)
    print(clientIP)

    # Sending a reply to client

    UDPServerSocket.sendto(bytesToSend, address)