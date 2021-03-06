#Borja :)
import sys, os
sys.path.append('')
import subprocess
import altair as alt
import pandas as pd
import progressbar
from shutil import copyfile
from Bio.Seq import Seq
from utils.utils import *
import numpy as np
import math

class UtilsReport:
    @staticmethod
    def exportHistogram(histogram, path):
        x = range(len(histogram))
        df = pd.DataFrame({'X':x,'Y':histogram})
        chart = alt.Chart(df).mark_bar().encode(alt.X('X',  bin=alt.Bin(maxbins=100)), y = 'Y')
        chart.save(path)


class RepresentantGraph:
    exeBcalm = 'third-party/bcalm/build/bcalm'
    exeGFA = 'third-party/bcalm/scripts/convertToGFA.py'
    outFile, _tail, _graphExt= 'tmp/unitigs', '.unitigs.fa', '.graph'
    seqs = []
    class GraphStruct:
        def __init__(self):
            self._graph = dict()
            self._freqs = dict()
            self._active = dict()
            self._lengths = dict()

        def addVertex(self, u):
            self._graph[u] = []
            self._freqs[u] = 0

        def addEdge(self, u, v):
            self._graph[u].append(v)

        def addActive(self, u, active):
            self._active[u] = active

        def setActive(self, u, active):
            self._active[u] = active

        def addFreq(self, u, frec):
            self._freqs[u] = frec

        def addLength(self, u, length):
            self._lengths[u] = length

        def getActive(self, u):
            return self._active[u]

        def exportGraph(self, outputFile, args):
            with open(outputFile, 'w+') as fWrite:
                numKeys = len(self._graph.keys())
                fWrite.write(str(numKeys)+' '+str(args['abundanceMin'])+' \n')
                for key, val in self._graph.items():
                    if not self._active[key]:
                        continue
                    fWrite.write(str(key)+' ')
                    for v in val:
                        fWrite.write(str(v)+' ')
                    fWrite.write(str(self._freqs[key])+' ')
                    fWrite.write(str(self._lengths[key])+' \n')

    def __init__(self, path = None, kmerSize = 30, abundanceMin = 1, meta = False):
        self._g, self._kmerSize = self.GraphStruct(), int(kmerSize)
        # Primer lanzamiento para definir la abundancia
        args = {'in':path, 'kmerSize':kmerSize,'abundanceMin':abundanceMin,'out':self.outFile}
        cmd = [self.exeBcalm,'-in',args['in'],'-histo','1','-kmer-size',args['kmerSize'],'-abundance-min',args['abundanceMin'],'-out',args['out']]
        print('Bcalm cmd (first launch): ',cmd)
        Utils.executecmd(cmd)
        args['abundanceMin'] = str(self.__study_frequency_histograms(int(abundanceMin), meta = meta))
        Utils.remove_file('tmp/unitigs')
        self.__produceGraphFile(args)
        self.__indexGFA(self.outFile, args['abundanceMin'])
        self._g.exportGraph(self.outFile+self._graphExt, args)
        print('End!')

    def __study_frequency_histograms(self, abundanceMin = 1, meta = False):
        if meta:
            return 3
        file, file_w = self.outFile+'.histo', self.outFile+'.histo.txt'
        def roundup(x):
            return int(math.ceil(x / 10.0)) * 10
        def __vector_trend(x, window_size = 15):
            assert len(x) > 2*window_size

            for i, v in enumerate(x):
                if i < window_size:
                    continue
                left_trend, right_trend = 0, 0
                for j in range(i-window_size, i):
                    left_trend += (x[j] >= v)
                for j in range(i, min(i+window_size, len(x))):
                    right_trend += (x[j] >= v)
                if left_trend <= right_trend and right_trend >= (window_size*0.5):
                    print('LT: ',left_trend,' RT: ',right_trend)
                    return i
        def __kernel_estimation(data_x, data_y):
            import matplotlib.pyplot as plt
            from datetime import datetime
            SCALE = 0.25 if meta else 1.0
            data_y_tmp = data_y[np.where(data_y < 1000)]
            data_x_tmp = data_x[0:max(data_y_tmp)]
            plt.hist(data_y, bins=125, density=True)
            plt.savefig(self.outFile+'_histo.png')
            plt.clf()
            from scipy import stats
            plt.hist(data_y_tmp, bins=100, density=True)
            gkde=stats.gaussian_kde(data_y)
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print('Kde factor: ', gkde.factor,' ',current_time)
            gkde.set_bandwidth(bw_method=gkde.factor*SCALE)
            #data_x_tmp = data_x[0:100] if meta else data_x
            kdepdf = gkde.evaluate(data_x_tmp)
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print('End evaluation. ', current_time)
            # plot estimated density
            plt.plot(data_x_tmp, kdepdf, label='kde', color="g")
            # Cross zeros
            Z = np.reshape(kdepdf.T, data_x_tmp.shape)
            diff = np.gradient(Z)
            sdiff = np.sign(diff)
            zc = np.where(sdiff[:-1] != sdiff[1:])
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print('Zero crosses: ',zc,' ',current_time)
            decision = zc[0][0]
            for i in range(len(zc[0])-1):
                first, second, third = zc[0][i], zc[0][i+1], zc[0][i+2]
                if gkde.evaluate(first) > gkde.evaluate(second) and gkde.evaluate(second) < gkde.evaluate(third):
                    decision = int((first+second)*0.5)
                    break
            plt.vlines(decision, plt.ylim()[0], plt.ylim()[1], linestyles='dashed')
            plt.title('Kernel Density Estimation')
            plt.savefig(self.outFile+'_density.png')
            return decision

        UPPER_FREQ_LIMIT = 999999 if meta else 1000
        x,y = [],[]
        X,Y = [],[]
        with open(file, 'r') as f,open(file_w, 'w') as f2:
            for i, line in enumerate(f.readlines()):
                l_split = line.strip().split('\t')
                value = UPPER_FREQ_LIMIT if int(l_split[1]) > UPPER_FREQ_LIMIT else int(l_split[1])
                if int(l_split[0]) < UPPER_FREQ_LIMIT:
                    X.append(int(l_split[0]))
                    Y += [int(l_split[0])]*value
                    if i <= abundanceMin:
                        continue
                x.append(int(l_split[0]))
                y.append(roundup(int(l_split[1])))
                f2.write(str(roundup(int(l_split[1])))+'\n')
        #kneedle = KneeLocator(x, y, S=2.0, curve='convex', direction='decreasing')
        offset = __vector_trend(y)
        print('Offset: ',offset)
        #offset = kneedle.knee
        min_freq_estimator = abundanceMin + offset
        min_freq_estimator_kde = __kernel_estimation(np.array(X), np.array(Y))
        print('Recommended abundance (kernel estimator): ',min_freq_estimator_kde)
        min_freq_estimator = min(min_freq_estimator_kde, min_freq_estimator) if meta else max(min_freq_estimator_kde, min_freq_estimator)
        #print('Handmade abundance: ', 16)
        #min_freq_estimator = 16
        print('Recommended abundance: ', min_freq_estimator)
        return min_freq_estimator

    def getOutFile(self):
        return self.outFile+self._tail

    def __produceGraphFile(self, args):
        tail = '.unitigs.fa'
        cmd = [self.exeBcalm,'-in',args['in'],'-histo','1','-kmer-size',args['kmerSize'],'-abundance-min',args['abundanceMin'],'-out',args['out']]
        print('Bcalm cmd: ',cmd)
        Utils.executecmd(cmd)
        cmd = ['python',self.exeGFA,args['out']+tail,args['out'],args['kmerSize']]
        print('To GFA cmd: ', cmd)
        Utils.executecmd(cmd)
        #print('To FM')
        #BioUtils.fastToFm(args['out']+tail,args['out']+'.FM')

    def __indexGFA(self, file, abundanceMin):
        numSeqs, min, max = 0, 9999999, 0
        histogram = [0]*10000
        frecs, lengths, active = [], [], []
        with open(file, 'r') as f:
            lines = f.readlines()
            connect, is_connected = [False]*len(lines), [False]*len(lines)
            for line in lines:
                if line[0] == 'S':
                    line_split = line.split('\t')
                    frecs.append(line_split[5].split(':')[2].strip())
                    unitigLength = int(line_split[3].split(':')[2].strip())
                    totalFreq = int(line_split[4].split(':')[2].strip())
                    lengths.append(unitigLength)
                    if float(totalFreq / unitigLength) >= float(abundanceMin):
                        active.append(True)
                    else:
                        active.append(False)
                    numSeqs += 1
                    if unitigLength > len(histogram):
                        histogram = histogram + [0]*(unitigLength - len(histogram) + 1)
                    histogram[unitigLength] += 1
                    min = unitigLength if min > unitigLength else min
                    max = unitigLength if max < unitigLength else max
                elif line[0] == 'L':
                    infoLine = line.split('\t')
                    ori =  int(infoLine[1])
                    if infoLine[2] == '+':
                        connect[ori] = True
                    else:
                        is_connected[ori] = True
            print('Number of sequences: ', numSeqs)
            print('Exporting histogram:')
            histogram = histogram[0:max+1]
            UtilsReport.exportHistogram(histogram, 'stats/histogram.html')
            print('Histogram available!\nTotal Sequences: ',2*numSeqs)
            self._unitigs = numSeqs
            for i in range(0,2*numSeqs):
                self._g.addVertex(i)
                if i >= numSeqs:
                    self._g.addFreq(i, frecs[i - numSeqs])
                    self._g.addActive(i, active[i - numSeqs] or (connect[i - numSeqs] and is_connected[i - numSeqs]))
                    self._g.addLength(i, lengths[i - numSeqs])
                else:
                    self._g.addFreq(i, frecs[i])
                    self._g.addActive(i, active[i] or (connect[i] and is_connected[i]))
                    self._g.addLength(i, lengths[i])
        with open(file, 'r') as f:
            for line in f.readlines():
                if line[0] == 'L':
                    infoLine = line.split('\t')
                    ori, target = int(infoLine[1]) if infoLine[2] == '+' else int(infoLine[1])+numSeqs\
                        , int(infoLine[3]) if infoLine[4] == '+' else int(infoLine[3])+numSeqs
                    if self._g.getActive(ori) and self._g.getActive(target):
                        if ori > 2*numSeqs:
                            print("Ori higher: ", ori)
                        self._g.addEdge(ori, target)

if __name__=='__main__':
    tmpDir, resDir = 'tmp/', 'tmpresultsDir_'
    readFiles = []
    def __preprocess_karect(path, correct = True):
        global resDir

        resDir = resDir + 'Karect/'
        resDir_paired = resDir+'paired/'
        Utils.remove_dir(resDir)
        Utils.mkdir(resDir)
        Utils.mkdir(resDir_paired)
        files = Utils.get_files_recursive(path, ['fastq'])
        files.sort()
        print('Files: ', files)
        if correct:
            cmd = ['karect','-correct','-matchtype=hamming','-celltype=haploid','-resultdir='+resDir]+['-inputfile='+t for t in files]
            Utils.executecmd(cmd)
            files = Utils.get_files_recursive(resDir,['.fastq'])
        Utils.remove_dir(tmpDir)
        Utils.mkdir(tmpDir)
        suffix = 'Ownlatest/'
        outputFile = tmpDir+suffix+'append.fasta'
        files.sort()
        print('New files corrected: ', files)
        print('Renaiming sequences/files: ')
        # Opcion A
        # newFiles = BioUtils.renameFastqSeqs(files, tmpDir)
        # Opcion B
        newFiles = [BioUtils.fastqtofasta(f,tmpDir+'/'+str(i)+'.fasta') for i,f in enumerate(files)]
        print('NewFiles: ', newFiles)
        Utils.mkdir(tmpDir+suffix)
        return [Utils.append_files_bash(newFiles, outputFile), newFiles[0]]

    def __preprocess_tgs(path, path_pe = None, kmer_size = 30, technique = 'standard'):
        global resDir
        if path_pe is None:
            resDir += 'Consent/'
            suffix = 'CONSENT_corrected.fasta'
            Utils.remove_dir(resDir)
            Utils.mkdir(resDir)
            files = Utils.get_files(path)
            print('Files: ',files)
            cmd = ['third-party/CONSENT/CONSENT-correct','--in',files[0],'--out',resDir+suffix,'--type','PB']
            Utils.executecmd(cmd)
            Utils.remove_dir(tmpDir)
            Utils.mkdir(tmpDir)
        if path_pe is not None:
            RATE_KMER, KMER_USAGE, SOLID_THRESHOLD, TRIALS, ITERATIONS = kmer_size,kmer_size, 2, 1, 3
            iterative, c_iterations = False, 0
            if technique == 'standard':
                ITERATIONS = 1
            while c_iterations < ITERATIONS:
                if c_iterations < 1:
                    resDir += 'Lordec/'
                suffix = 'lordec_corrected.fasta'
                Utils.remove_dir(resDir)
                Utils.mkdir(resDir)
                files = Utils.get_files(path)
                print('Files: ',files)
                files_pe = Utils.get_files(path_pe)
                files_append = (' ').join(files_pe)
                print('Files append: ', files_append)
                Utils.remove_file(files_pe[0]+'_k'+str(KMER_USAGE)+'_s'+str(SOLID_THRESHOLD)+'.h5')
                cmd = ['lordec-correct','-t',str(TRIALS),'-2']+files_pe+['-i',files[0], '-k', str(KMER_USAGE),'-s',str(SOLID_THRESHOLD),'-o',resDir+suffix]
                Utils.executecmd(cmd)
                Utils.remove_dir(tmpDir)
                Utils.mkdir(tmpDir)
                c_iterations = c_iterations + 1
                files[0] = resDir+suffix
                # trim_split
                suffix_trim_split = 'lordec_corrected_trim_split.fasta'
                cmd = ['lordec-trim-split','-i',files[0],'-o',resDir+suffix_trim_split]
                Utils.executecmd(cmd)
                files[0] = resDir + suffix_trim_split
                #KMER_USAGE = str(int(KMER_USAGE)+int(RATE_KMER))
        suffix = 'Ownlatest/'
        files = Utils.get_files(resDir)
        print('New files corrected: ', files)
        Utils.mkdir(tmpDir+suffix)
        return files

    def __create_s_pe(tgs_file):
        global tmpDir
        insert_size = 700
        read_size = 350

        dir_reads = tmpDir+'reads/'
        Utils.mkdir(dir_reads)

        files = [dir_reads+'read1.fasta', dir_reads+'read2.fasta']
        [Utils.remove_file(f) for f in files]
        print('New paired end files in: ', files)
        with open(files[0], 'w+') as f1, open(files[1],'w+') as f2, open(tgs_file,'r') as f_read:
            id = ''
            lines = f_read.readlines()
            with progressbar.ProgressBar(max_value=len(lines)) as bar:
                for tgs_read,line in enumerate(lines):
                    bar.update(tgs_read)
                    if line[0] == '>':
                        id = line.strip()
                    if line[0] != '>':
                        read_process = line.strip()
                        for num_read,i in enumerate(range(0,len(read_process) - insert_size + 1)):
                            # Left read
                            f1.write(id+'.'+str(num_read)+'.1\n')
                            f1.write(read_process[i:i+read_size]+'\n')
                            # Right read
                            new_start = i + (insert_size - read_size)
                            f2.write(id+'.'+str(num_read)+'.2\n')
                            f2.write(BioUtils.reverse_complement(read_process[new_start:new_start+read_size])+'\n')

    def __preprocess2(files):
        suffix = 'Ownlatest/'
        outputFile = tmpDir+suffix+'merge.fasta'
        return Utils.append_files(files, outputFile)

    type = sys.argv[4]
    if type == 'ngs':
        pear, correction, meta = (sys.argv[6] == '--joined'), (sys.argv[5] == '--correct'), (sys.argv[7] == '--meta')

        print('*************** Summary *********************')
        print('Pear: ', pear)
        print('Correct: ', correction)
        print('Meta: ', meta)
        print('*********************************************')
        pathIn = __preprocess_karect(sys.argv[1], correction)
        path, kmerSize, abundanceMin = pathIn[0], sys.argv[2], sys.argv[3]
        print('Path: ', path)
        rG = RepresentantGraph(path, kmerSize, abundanceMin, meta = meta)
    elif type == 'tgs':
        method = 'lordec'
        if method == 'consent':
            pathIn = __preprocess_tgs(sys.argv[1])
        elif method == 'lordec':
            '''
            We demand paired-end reads to be read1.fastq, read2.fastq, here we receive the folder
            '''
            # Iterative execution
            technique = sys.argv[5]
            pathIn = __preprocess_tgs(sys.argv[1], sys.argv[2], sys.argv[3], technique=technique)
        #pathIn = ['/home/bfreire/Gatb-trial/tmpresultsDir_Consent/CONSENT_corrected.fasta']
        __create_s_pe(pathIn[0])


    #BioUtils.identicalClustering(__preprocess2([pathIn[1],rG.getOutFile()]))
