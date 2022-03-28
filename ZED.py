import pyzed.sl as sl
from collections import namedtuple
from time import sleep, time
import cv2
from threading import Thread
from queue import Empty, Queue
import numpy as np
from datetime import datetime

class ZEDVideoStream(Thread):
    def __init__(self, ZED, inputQueue, outputQueue):
        self.ZED = ZED
        self.inputQueue = inputQueue
        self.outputQueue = outputQueue
        Thread.__init__(self)

    def run(self):
        while True:
            album = self.ZED._takePicture(emptyBuffer=False)

            try:
                command = self.inputQueue.get(block=False)
            except Empty:
                command = None

            if command == 1:
                self.outputQueue.put(album)
            elif command == 0:
                break
            elif command == None:
                continue
        return

class ZEDCamera:
    def __init__(self, resolution='1080', depth_mode='perf', fps=10, depth= True, color=True):
        self.depth = depth
        self.color = color
        self.init = sl.InitParameters()
        self.fps = fps

        resolutions = {'720': sl.RESOLUTION.HD720,
                       '1080':sl.RESOLUTION.HD1080,
                       '2K'  :sl.RESOLUTION.HD2K}

        depthModes = {'perf': sl.DEPTH_MODE.PERFORMANCE,
                      'qual': sl.DEPTH_MODE.QUALITY,
                      'ultra': sl.DEPTH_MODE.ULTRA,}

        self.init.camera_resolution = resolutions[resolution]
        self.init.depth_mode = depthModes[depth_mode]
        self.cam = sl.Camera()
        self.inQ, self.outQ = Queue(maxsize=1), Queue(maxsize=1)
        return

    def _openCamera(self, totalAttempts=5):
        for attempt in range(totalAttempts):
            status = self.cam.open(self.init)
            if status != sl.ERROR_CODE.SUCCESS:
                print('\nTry {} out of {}'.format(attempt+1,totalAttempts))
                print(repr(status))
                if attempt == (totalAttempts-1):
                    print('\n\n'+'-'*80)
                    print('Failed to open ZED')
                    print('Please Unplug the ZED and plug it back in!')
                    return False
            else:
                return True

    def _closeCamera(self):
        self.cam.close()

    def __enter__(self):
        totalAttempts = 5
        video_filename = './videos/' + datetime.now().strftime('%Y-%m-%d---%H-%M-%S') + '.svo'
        recording_param = sl.RecordingParameters(video_filename, sl.SVO_COMPRESSION_MODE.H264)
        err = self.cam.enable_recording(recording_param)
        self.recording = True
        runtime = sl.RuntimeParameters()
        frames_recorded = 0
        while self.recording:
            if self.cam.grab(runtime) == sl.ERROR_CODE.SUCCESS:
                frames_recorded += 1
    def __exit__(self, exc_type, exc_value, traceback):
        print('Closing ZED...')
        self.inQ.put(0)
        self.videoStream.join()
        self.cam.disable_recording()

    # def __del__(self):
    #     self.inQ.put(0)
    #     self.videoStream.join()
    #     self.cam.close()

    def startStream(self):
        t = Thread(target = self.__enter__)
        t.start()

    def closeStream(self):
        t = Thread(target = self.cam.disable_recording())
        t.start()
        self.recording = False

    def _takePicture(self, emptyBuffer=False):
        pics = []
        start = time()
        while True:
            status = self.cam.open(self.init)
            if emptyBuffer:
                for i in range(7):
                    status = self.cam.grab(self.runtime)
            if status == sl.ERROR_CODE.SUCCESS:
                svo_image= svo_depth = sl.Mat()

                if self.depth:
                    self.cam.retrieve_image(svo_depth, sl.VIEW.DEPTH)
                    depth_image = np.asanyarray(svo_depth.get_data())
                    pics.append(depth_image)

                if self.color:
                    self.cam.retrieve_image(svo_image, sl.VIEW.SIDE_BY_SIDE)
                    color_image = np.asanyarray(svo_image.get_data())
                    pics.append(color_image)

            # elif (time() - start) > 1:
            #     raise TimeoutError('The ZED is taking longer than 1 sec')
        return self.Album(*pics)

    def takePicture(self, buffer=False):
        self.inQ.put(1)
        album = self.outQ.get()
        return album

if __name__ == '__main__':
    cam = ZEDCamera()
    cam._openCamera()
    cam.startStream()


