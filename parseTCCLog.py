import re
import datetime
import numpy

import matplotlib.pyplot as plt

matchStr = "2018-04-09 15:17:12.347 info  MCPMultiplexor(mcpMultiplexor) writing 'ALT STATUS'"
testStr = "2018-04-10 01:35:08.674 info  MCPMultiplexor(mcpMultiplexor) writing 'ALT MOVE 16.1406034 1.3346695 5728.07877'"
# reTest = r"MCPMultiplexor\(mcpMultiplexor\)\s+writing\s+'(?P<name>ALT MOVE)"
statusStr = "2018-04-10 01:35:10.595 info  SDSSAxisDevice(alt) replyBuffer=['STATUS', '5.003980 0.000000 5710.464296 0 0.000000']; curr cmd='STATUS' running"

reWriteMCP = r"MCPMultiplexor\(mcpMultiplexor\)\s+writing\s+'(?P<axis>ALT|AZ|ROT)\s(?P<cmd>MOVE|INIT)(\s+)?(?P<pos>-?\d+.\d+)?(\s+)?(?P<vel>-?\d+.\d+)?(\s+)?(?P<tai>-?\d+.\d+)?'"
reAxisStatus = r"SDSSAxisDevice\((?P<axis>alt|az|rot1)\) replyBuffer=\['STATUS', '(?P<pos>-?\d+.\d+) (?P<vel>-?\d+.\d+) (?P<tai>-?\d+.\d+) (?P<word>\d+) (?P<index>-?\d+.\d+)'\]"

# out = re.search(reAxisStatus, statusStr)

# import pdb; pdb.set_trace()

class Axis(object):
    def __init__(self, name):
        self.name = name
        self.statusPos = []
        self.statusVel = []
        self.statusTai = []
        self.statusWord = []
        self.statusTS = []
        self.movePos = []
        self.moveVel = []
        self.moveTai = []
        self.moveTS = []
        self.moveTaiTS = []
        self.stopTS = []
        self.stopTai = [] # last seen tai
        self.initTS = []
        self.initTai = [] # last seen tai

    def numpyify(self):
        cmds = ["move", "status", "stop", "init"]
        suff = ["Pos", "Vel", "Tai", "Word", "TS", "TaiTS"]
        for cmd in cmds:
            for s in suff:
                if hasattr(self, cmd+s):
                    array = getattr(self, cmd+s)
                    array = numpy.asarray(array)
                    setattr(self, cmd+s, array)

    def applyTaiFilter(self, taiMin, taiMax):
        statusInd = numpy.logical_and(self.statusTai>taiMin, self.statusTai<taiMax)
        self.statusPos = self.statusPos[statusInd]
        self.statusVel = self.statusVel[statusInd]
        self.statusTai = self.statusTai[statusInd]
        self.statusWord = self.statusWord[statusInd]
        self.statusTS = self.statusTS[statusInd]

        moveInd = numpy.logical_and(self.moveTai>taiMin, self.moveTai<taiMax)
        self.movePos = self.movePos[moveInd]
        self.moveVel = self.moveVel[moveInd]
        self.moveTai = self.moveTai[moveInd]
        self.moveTS = self.moveTS[moveInd]
        self.moveTaiTS = self.moveTaiTS[moveInd]

        stopInd = numpy.logical_and(self.stopTai>taiMin, self.stopTai<taiMax)
        self.stopTS = self.stopTS[stopInd]
        self.stopTai = self.stopTai[stopInd] # last seen tai

        initInd = numpy.logical_and(self.initTai>taiMin, self.initTai<taiMax)
        self.initTS = self.initTS[initInd]
        self.initTai = self.initTai[initInd] # last seen tai

# def plot(axisDict):

#     fig, axl = plt.subplots(3,1, figsize=(10,7))
#     axes = ["alt", "az", "rot"]
#     for axisName, ax in zip(axes, axl):
#         axis = axisDict[axisName]
#         ax.plot(axis.statusTai, axis.statusPos, 'ro')
#         ax.plot(axis.moveTai, axis.movePos, '-bo')
#         for initx in axis.initTai:
#             ax.axvline(x=initx, color='red', linewidth=2)

#         for initx in axis.stopTai:
#             ax.axvline(x=initx, color='black', linewidth=2)
#         ax.set_xlabel("tai (seconds)")
#         ax.set_ylabel("%s (degrees)"%axisName)
#     plt.show()

def plot(axisDict, tai=True, interpMoveTS=True, axisStop=False, axisInit=False):
    # interp moveTS means use datetime scale, with moves
    # when they are intetended to be exectuted
    # otherwise use the timestamp at which they came in (in advance)
    fig, axl = plt.subplots(3,1, figsize=(10,7))
    axes = ["alt", "az"]
    currAx = 0
    for axisName in axes:
        ax = axl[currAx]
        axis = axisDict[axisName]
        if tai == True:
            statusT = axis.statusTai
            moveT = axis.moveTai
            initT = axis.initTai
            stopT = axis.stopTai
        else:
            statusT = axis.statusTS
            initT = axis.initTS
            stopT = axis.stopTS
            if interpMoveTS:
                moveT = axis.moveTaiTS
            else:
                moveT = axis.moveTS
        ax.plot(statusT, axis.statusPos, 'ro')
        ax.plot(moveT, axis.movePos, '-bo')
        if axisInit:
            for initx in initT:
                ax.axvline(x=initx, color='red', linewidth=2)
        if axisStop:
            for initx in stopT:
                ax.axvline(x=initx, color='black', linewidth=2)
        ax.set_xlabel("time")
        ax.set_ylabel("%s pos (degrees)"%axisName)
        currAx+= 1

        if axisName == "alt":
            # plot velocities too
            ax = axl[currAx]
            ax.plot(statusT, axis.statusVel, 'ro')
            ax.plot(moveT, axis.moveVel, '-bo')
            ymin = numpy.min(axis.moveVel)-0.2
            ymax = numpy.max(axis.moveVel)+0.2
            if axisInit:
                for initx in initT:
                    ax.axvline(x=initx, color='red', linewidth=2)
            if axisStop:
                for initx in stopT:
                    ax.axvline(x=initx, color='black', linewidth=2)
            ax.set_xlabel("time")
            ax.set_ylabel("%s vel (degrees/sec)"%axisName)
            ax.set_ylim([ymin, ymax])
            currAx+= 1

    plt.show()

def tsFromLine(line):
    # read the timestamp
    # return tuple with timstamp as datetime obj
    # and rest of line
    date, time, rest = line.split(None, 2)
    year, month, day = date.split("-")
    hour, minute, second = time.split(":")
    second, milisecond = second.split(".")
    dtList = [year, month, day, hour, minute, second, milisecond]
    # cast to ints
    dtList = [int(x) for x in dtList]
    # convert milisecond to microseconds
    dtList[-1] = dtList[-1]*1000
    return datetime.datetime(*dtList)

def parseLog(logfile, axisDict):
    f = open(logfile, "r")
    for line in f:
        mcpWrite = re.search(reWriteMCP, line)
        axisStatus = re.search(reAxisStatus, line)
        if mcpWrite is None and axisStatus is None:
            # nothing to parse on this line
            continue
        ts = tsFromLine(line)
        if mcpWrite:
            parseDict = mcpWrite.groupdict()
        else:
            parseDict = axisStatus.groupdict()
        axisName = parseDict["axis"].lower()
        if axisName == "rot1":
            axisName = "rot"
        axis = axisDict[axisName]

        if mcpWrite:
            # this was a write to mcp line,
            # decide if it was a move, stop or init.
            if not axis.statusTai:
                continue # need status recorded to solve for tai
            lastTai, lastDT = axis.statusTai[-1], axis.statusTS[-1]
            # determine a tai value for the ts
            scaledTai = lastTai + (ts - lastDT).total_seconds()

            if parseDict["cmd"] == "INIT":
                axis.initTS.append(ts)
                axis.initTai.append(scaledTai)
            elif parseDict["cmd"] == "MOVE" and parseDict["pos"]:
                # this is a move pvt
                pos = float(parseDict["pos"])
                vel = float(parseDict["vel"])
                tai = float(parseDict["tai"])
                axis.moveTS.append(ts)
                axis.movePos.append(pos)
                axis.moveVel.append(vel)
                axis.moveTai.append(tai)
                # determine the current tai to datetime conversion
                # and scale tai into datetimes
                scaledDT = lastDT + datetime.timedelta(seconds=(tai - lastTai))
                axis.moveTaiTS.append(scaledDT)
            else:
                # this is a move without a pvt, so it's a stop
                axis.stopTS.append(ts)
                axis.stopTai.append(scaledTai)
        else:
            # this is a status reply
            pos = float(parseDict["pos"])
            vel = float(parseDict["vel"])
            tai = float(parseDict["tai"])
            word = int(parseDict["word"])
            axis.statusTS.append(ts)
            axis.statusPos.append(pos)
            axis.statusVel.append(vel)
            axis.statusTai.append(tai)
            axis.statusWord.append(word)


def april():
    axisDict = {
        "alt": Axis("alt"),
        "az": Axis("az"),
        "rot": Axis("rot"),
    }
    parseLog("preFilt/tcc.log-20180410", axisDict)
    aprilTaiBounds = [3320, 3500]
    for axis in axisDict.itervalues():
        axis.numpyify()
        axis.applyTaiFilter(*aprilTaiBounds)
    plot(axisDict, tai=False, interpMoveTS=False)

def march():
    axisDict = {
        "alt": Axis("alt"),
        "az": Axis("az"),
        "rot": Axis("rot"),
    }
    parseLog("preFilt/tcc.log-20180330", axisDict)
    taiBounds = [81000, 85000]
    for axis in axisDict.itervalues():
        axis.numpyify()
        axis.applyTaiFilter(*taiBounds)
    plot(axisDict)

def jan():
    axisDict = {
        "alt": Axis("alt"),
        "az": Axis("az"),
        "rot": Axis("rot"),
    }
    parseLog("preFilt/tcc.log-20180131", axisDict)
    taiBounds = [85235, 85400]
    for axis in axisDict.itervalues():
        axis.numpyify()
        axis.applyTaiFilter(*taiBounds)
    plot(axisDict, tai=False, interpMoveTS=False)

def nov():
    axisDict = {
        "alt": Axis("alt"),
        "az": Axis("az"),
        "rot": Axis("rot"),
    }
    parseLog("preFilt/tcc.log-20171128", axisDict)
    taiBounds = [83560, 83700]
    for axis in axisDict.itervalues():
        axis.numpyify()
        axis.applyTaiFilter(*taiBounds)
    plot(axisDict, tai=False, interpMoveTS=False)

nov()



