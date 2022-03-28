import socket
import numpy as np
import cv2
from threading import Thread

class cameraServer:
    def __init__(self):
        self.verbs = {
        'on': self._turnCamerasOn,
        'off': self._turnCamerasOff,
        'pic': self._takeSinglePic
        }
        self.frame = np.zeros([2*480,640,3],dtype=np.uint8)
        return

    def connectCameras(self):
        self.cameras = {}
        self.startedQ = {}
        try:
            from realSense import RealSense2
            rsCam = RealSense2()
            rsCam.takePicture()
            isRS = True
            self.cameras['RS'] = rsCam
            self.startedQ['RS'] = isRS
        except:
            isRS = False
            print('Realsense Camera could not be opened!')

        try:
            from ZED import ZEDCamera
            zedCam = ZEDCamera()
            zedCam._openCamera()
            isZed=True
            self.cameras['ZED'] = zedCam
            self.startedQ['ZED'] = isZed

        except:
            isZed=False
            print('ZED Camera could not be opened!')

        if not self.checkCamerasStarted(isRS, isZed):
            exit()
        return

    def checkCamerasStarted(self, isRS, isZed):
        # if not isRS:
            # while True:
            #     resp = input('The RealSense camera was not opened. Continue? (y/n)')
            #     if resp.lower()=='n':
            #         print('Exiting')
            #         return False
            #     elif resp.lower()=='y':
            #         break

        if not isZed:
            while True:
                resp = input('The ZED camera was not opened. Continue? (y/n)')
                if resp.lower()=='n':
                    print('Exiting')
                    return False
                elif resp.lower()=='y':
                    break
        return True

    def startServer(self, address):
        sock = self._makeSocket(address)
        print('Ready for Connections')
        try:
            cv2.imshow('cameraServer', self.frame)
            cv2.waitKey(100)
            while True:
                client, addr = sock.accept()
                print('Connection', addr)
                Thread(target=self.clientHandler, args=(client,), daemon=True).start()
        finally:
            cv2.destroyAllWindows()
            print('Closing Cameras')
            for key in self.startedQ:
                self.cameras[key].closeStream()
        return

    def clientHandler(self, client):
        while True:
            req = client.recv(4096)
            if not req:
                continue
            command = req.decode('ascii')[:-1].split(' ')
            try:
                self.verbs[command[0]](command)

            except KeyError:
                print('ERROR: {} is not a proper command'.format(command[0]))
            finally:
                cv2.imshow('cameraServer', self.frame)
                cv2.waitKey(1)
    def __del__(self):
        cv2.destroyAllWindows()
        print('Closing Cameras')
        for key in self.startedQ:
            self.cameras[key].closeStream()

    def _makeSocket(self, address):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        sock.listen(5)
        return sock

    def _turnCamerasOn(self, command):
        if self.startedQ['ZED']:
            self.cameras['ZED'].startStream()
        print('Start recording!')
        # self.frame = self.frame[:,:,(0,0,0)]

    def _turnCamerasOff(self, command):
        # self.takePicture(fname=command[1], emptyBuffer=False)
        # if self.startedQ['RS']:
        #     self.cameras['RS'].closeStream()
        if self.startedQ['ZED']:
            self.cameras['ZED'].closeStream()
        print('Stop recording!')
        # self.frame = self.frame[:,:,(2,1,0)]

    def _takeSinglePic(self, command):
        self.takePicture(fname=command[1], emptyBuffer=True)
        return

    def takePicture(self, fname, emptyBuffer=False):
        if self.startedQ['RS']:
            album = self.cameras['RS'].takePicture(emptyBuffer)
            np.save('{}_{}_depth.npy'.format(fname, 'RS'), album.depth)
            np.save('{}_{}_color.npy'.format(fname, 'RS'), album.color)
            self.frame[:480,:,:] = album.color

        if self.startedQ['ZED']:
            album = self.cameras['ZED'].takePicture(emptyBuffer)
            depth = album.depth[120:600,320:960,0]
            color = np.concatenate([album.color[120:600,320:960,(2,1,0)], album.color[120:600,1600:2240,(2,1,0)]], axis=1)
            np.save('{}_{}_depth.npy'.format(fname, 'ZED'), depth)
            np.save('{}_{}_color.npy'.format(fname, 'ZED'), color)
            self.frame[480:,:,:] = color[:,:640,:]
        return

if __name__ == '__main__':
    server = cameraServer()
    server.connectCameras()
    server.startServer(('', 25000))
