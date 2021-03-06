# -*- coding: utf-8 -*-

from os import walk
import codecs
from transwarpnlp.ner.config import LargeConfig
import os, sys
import re

pkg_path = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(pkg_path)

def getFiles(source_path):
    files = []
    for (dir_path, _, file_names) in walk(source_path):
        for file_name in file_names:
            files.append(dir_path + "/" + file_name)
    return files

def handle_content(line):
    if line == "\n":
        return ""
    else:
        words = line.split(" ")
        results = []
        for word in words:
            if word.startswith('['):
                word = word[1:]
            if word.find(']') != -1:
                word = word.split("]")[0]

            results.append(word)
        return " ".join(results)

def getPosData(files, pos_file):
    with codecs.open(pos_file, "w", encoding="utf-8") as writer:
        for filename in files:
            print(filename)
            with codecs.open(filename, "r", encoding="utf-8") as file_contents:
                lines = file_contents.readlines()
                for line in lines:
                    line = handle_content(line)
                    if line != "":
                        line = re.sub(r'"', '', line)
                        writer.write(line)
                    else:
                        continue
                file_contents.close()
        writer.close()

def getNerData(pos_file, ner_file):
    tags = LargeConfig.nerTags
    with codecs.open(pos_file, 'r', encoding='utf-8') as pos,\
            codecs.open(ner_file, 'w', encoding='utf-8') as ner:
        lines = pos.readlines()
        for line in lines:
            words = line.split(" ")
            results = []
            for word in words:
                if word.find("/") != -1:
                    word_tag = word.split("/")
                    if word_tag[1] not in tags:
                        word = word_tag[0] + "/o"
                    results.append(word)
            ner.write(" ".join(results))
            ner.write("\n")



if __name__ == "__main__":
    source_file = "/Users/endy/Documents/自然语言处理/语料/2014"
    #source_file = pkg_path + "/data/test"
    files = getFiles(source_file)

    pos_file = os.path.join(pkg_path, "data/source/pos_data.txt")
    ner_file = os.path.join(pkg_path, "data/source/ner_data.txt")

    getPosData(files, pos_file)

    getNerData(pos_file, ner_file)



