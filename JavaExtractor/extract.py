#!/usr/bin/python

import itertools
import multiprocessing
import os
import sys
import shutil
import subprocess
from threading import Timer
import sys
from argparse import ArgumentParser
from subprocess import Popen, PIPE, STDOUT, call
from py4j.java_gateway import JavaGateway, GatewayParameters


def get_immediate_subdirectories(a_dir):
    return [(os.path.join(a_dir, name)) for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]


TMP_DIR = ""

def validateInput(path):
    failingFiles = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        # print("Validating input at:", dirpath)
        for filename in filenames:
            filepath = os.path.normpath(dirpath + '/' + filename)
            if os.path.isfile(filepath):
                currentResult = True
                gateway = JavaGateway(gateway_parameters=GatewayParameters(port=25335))
                syntaxChecker = gateway.entry_point
                f = open(filepath, "r", encoding="utf8")

                currentFile = True
                while currentFile:
                    line1 = f.readline()
                    line2 = f.readline()
                    currentFile = line2 and line1
                    if len(line1) > 1 and len(line2) > 1:
                        if not syntaxChecker.validSyntax(line1 + line2):
                            currentResult = False
                gateway.close()
                f.close()
                if not currentResult:
                    failingFiles.append(filename)

    if len(failingFiles) > 0:
        print("Input validation failed for:", failingFiles)
    return failingFiles

def ParallelExtractDir(args, dir):
    ExtractFeaturesForDir(args, dir, "")

def extract_java(path, max_path_length, max_path_width):
    gateway = JavaGateway(gateway_parameters=GatewayParameters(port=25335))
    javaextractor = gateway.entry_point

    f = open(path, "r", encoding="utf8")
    code = f.read()
    f.close()

    return javaextractor.extractCode(int(max_path_length), int(max_path_width), code)

def ExtractFeaturesForDir(args, dir, prefix):
    # command = ['java', '-cp', args.jar, 'JavaExtractor.App',
    #            '--max_path_length', str(args.max_path_length), '--max_path_width', str(args.max_path_width),
    #            '--dir', dir, '--num_threads', str(args.num_threads)]
    failingFiles = validateInput(dir)
    if len(failingFiles) > 0:
        raise ValueError("Input validation failed for:", failingFiles)

    outputFileName = TMP_DIR + prefix + dir.split('/')[-1]
    with open(outputFileName, 'a') as outputFile:
        for (dirpath, dirnames, filenames) in os.walk(dir):
            # print("Processing all java files at", dirpath, '.')
            for filename in filenames:
                filepath = os.path.normpath(dirpath + '/' + filename)
                if os.path.isfile(filepath):
                    out = extract_java(dirpath + '/' + filename, args.max_path_length, args.max_path_width)
                    outputFile.write(out)
                # else:
                #     print("Incorrect filepath:", filepath)
            # print("Processed all java files at", dirpath, '.')


def ExtractFeaturesForDirsList(args, dirs):
    global TMP_DIR
    TMP_DIR = "./tmp/feature_extractor%d/" % (os.getpid())
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)
    os.makedirs(TMP_DIR)
    try:
        p = multiprocessing.Pool(1)
        p.starmap(ParallelExtractDir, zip(itertools.repeat(args), dirs))
        #for dir in dirs:
        #    ExtractFeaturesForDir(args, dir, '')
        output_files = os.listdir(TMP_DIR)
        for f in output_files:
            os.system("cat %s/%s" % (TMP_DIR, f))
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-maxlen", "--max_path_length", dest="max_path_length", required=False, default=8)
    parser.add_argument("-maxwidth", "--max_path_width", dest="max_path_width", required=False, default=2)
    parser.add_argument("-threads", "--num_threads", dest="num_threads", required=False, default=64)
    parser.add_argument("-j", "--jar", dest="jar", required=True)
    parser.add_argument("-dir", "--dir", dest="dir", required=False)
    parser.add_argument("-file", "--file", dest="file", required=False)
    args = parser.parse_args()

    if args.file is not None:
        command = 'java -cp ' + args.jar + ' JavaExtractor.App --max_path_length ' + \
                  str(args.max_path_length) + ' --max_path_width ' + str(args.max_path_width) + ' --file ' + args.file
        os.system(command)
    elif args.dir is not None:
        subdirs = get_immediate_subdirectories(args.dir)
        to_extract = subdirs
        if len(subdirs) == 0:
            to_extract = [args.dir.rstrip('/')]
        ExtractFeaturesForDirsList(args, to_extract)


