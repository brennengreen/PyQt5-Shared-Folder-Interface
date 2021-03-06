import socket
import os
import time

class FileRecord:
    def __init__(self, path, filename, filesize, down_count=0):
        self.name = filename
        self.size = filesize
        self.path = path
        self.down_cnt = int(down_count)
    def __str__(self) -> str:
        return f"{self.name}\t{self.size}\t{self.path}\t{self.down_cnt}"
    def __repr__(self) -> str:
        return f"{self.name},{self.size},{self.path},{self.down_cnt}\n"

class Directory:
    def __init__(self):
        self.entries = {}
    def __str__(self) -> str:
        result = "FILENAME\tFILESIZE\tFILEPATH\tDOWNLOAD COUNT\n"
        for _, entry in self.entries.items():
            result += f"{entry}\n"
        return result

    def Add(self, entry):
        if entry.name not in self.entries.keys():
            self.entries[entry.name] = entry
    def Remove(self, key):
        if key not in self.entries.keys():
            del self.entries[key]


DIR_STRUCT = Directory()
HOST = "127.0.0.1"
PORT = 65432
SERVER_PATH = "./server/"

class Server:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.SEPARATOR = "<SEPARATOR>"
        self.BUFFER_SIZE = 4096
    
    def Bind(self, host, port):
        self.s.bind((host, port))
        print(f"Bound: {host}:{port}")

    def Listen(self):
        self.s.listen(1)
        (clientsocket, address) = self.s.accept()
        with clientsocket:
            print(f"Connected by {address}")
            data = clientsocket.recv(self.BUFFER_SIZE).decode()

            # process data to get command
            if (data == "UPLOAD"):
                self.ReceiveFile(clientsocket) 
            elif (data == "DOWNLOAD"):
                self.SendFile(clientsocket)
            elif (data == "DELETE"):
                self.DeleteFile(clientsocket)
            elif (data == "DIR"):
                self.ListDir(clientsocket)
            else:
                return False
            
            return True
    
    def SendFile(self, clientsocket):
        filename_raw = clientsocket.recv(self.BUFFER_SIZE).decode()
        filename = f"{SERVER_PATH}{filename_raw}"

        if(os.path.exists(filename)):
            with open(filename, "rb") as f:
                clientsocket.send(f"{filename_raw}{self.SEPARATOR}{os.path.getsize(filename)}".encode())
                tot_sent = 0
                while True:
                    bytes_read = f.read(self.BUFFER_SIZE)
                    tot_sent += len(bytes_read)
                    if not bytes_read:
                        break
                    clientsocket.sendall(bytes_read)
                    print(tot_sent)
            DIR_STRUCT.entries[filename_raw].down_cnt += 1
        else:
            clientsocket.send("FAILURE".encode())        
        print("Done Sending File!")

    def DeleteFile(self, clientsocket):
        filename = clientsocket.recv(self.BUFFER_SIZE).decode()
        print(f"Deleting {filename}")
        if (os.path.exists(f"{SERVER_PATH}{filename}")):
            os.remove(f"{SERVER_PATH}{filename}")
            DIR_STRUCT.Remove(filename)
        else:
            print("File doesn't exist!")
            clientsocket.send("DOESN'T EXIST!".encode())
            return
        print("Deletion successful!")
        clientsocket.send("SUCCESS!".encode())

    def ListDir(self, cliensocket):
        cliensocket.send(f"{DIR_STRUCT}".encode())

    def ReceiveFile(self, clientsocket):
        data = clientsocket.recv(self.BUFFER_SIZE).decode()
        filename, filesize = data.split(self.SEPARATOR)
        new_entry = FileRecord(filename, os.path.basename(filename), int(filesize))
        filename = os.path.basename(filename)
        filesize = int(filesize)
        print(f'{new_entry}')

        seconds = (time.time() * 1000) - 500
        first_read = time.time()
        print(seconds)
        down_data = []
        with open(f"{SERVER_PATH}{filename}", 'wb') as f:
                sent = 0
                delta_s = 0.0
                tot_bytes_read = 0.0
                while True:
                    bytes_read = clientsocket.recv(self.BUFFER_SIZE)
                    if not bytes_read:
                        break

                    # Calculate Download Speed
                    delta_s += abs((time.time() * 1000) - seconds)
                    seconds = time.time() * 1000
                    tot_bytes_read += float(len(bytes_read))
                    if delta_s >= 250.0:
                        dnld_speed = tot_bytes_read / delta_s
                        delta_s = 0.0
                        tot_bytes_read = 0.0
                        down_data.append(((seconds/1000) - first_read, dnld_speed)) # Record time since start of transfer, download speed

                    f.write(bytes_read)
                    sent += len(bytes_read)
                    print(f"{float(sent)/filesize}")
        
        with open(f"{SERVER_PATH}download_data.txt", 'wb') as f:
            for time_x, speed in down_data:
                f.write(f"{time_x}, {speed}\n".encode())

        DIR_STRUCT.Add(new_entry)
        print(f"Finished uploading {filename}!")


def PopulateFileDirectory():
    with open('./server/directory.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            (filename, filesize, filepath, down_count) = line.split(',')
            DIR_STRUCT.Add(FileRecord(filepath, filename, filesize, down_count))

def WriteFileDirectory():
    with open('./server/directory.txt', 'wb') as f:
        for _,entry in DIR_STRUCT.entries.items():
            f.write(entry.__repr__())

def main():
    PopulateFileDirectory()

    print(DIR_STRUCT)

    s = Server()
    s.Bind(HOST, PORT)

    while s.Listen():
        continue

    WriteFileDirectory()

if __name__ == "__main__":
    main()