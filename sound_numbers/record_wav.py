#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sys import byteorder
from array import array
from struct import pack
from subprocess import call

import pyaudio
import wave
import re

THRESHOLD = 500
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 16000


def is_silent(snd_data):
    """Returns 'True' if below the 'silent' threshold"""
    return max(snd_data) < THRESHOLD


def normalize(snd_data):
    """Average the volume out"""
    MAXIMUM = 16384
    times = float(MAXIMUM)/max(abs(i) for i in snd_data)

    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r


def trim(snd_data):
    """Trim the blank spots at the start and end"""
    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for i in snd_data:
            if not snd_started and abs(i) > THRESHOLD * 2:
                snd_started = True
                r.append(i)
            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data


def add_silence(snd_data, seconds):
    """Add silence to the start and end of 'snd_data' of length 'seconds' (float)"""
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(snd_data)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r


def record():
    """
    Record a word or words from the microphone and
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the
    start and end, and pads with 0.5 seconds of
    blank sound to make sure VLC et al can play
    it without getting chopped off.
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE, input=True, output=True, frames_per_buffer=CHUNK_SIZE)

    num_silent = 0
    snd_started = False

    r = array('h')

    while 1:
        snd_data = array('h', stream.read(CHUNK_SIZE))
        print(snd_data)
        if byteorder == 'big':
            snd_data.byteswap()
        r.extend(snd_data)

        silent = is_silent(snd_data)
        print(silent)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True

        if snd_started and num_silent > 20:
            break

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    #r = normalize(r)
    r = trim(r)
    r = add_silence(r, 0.01)
    return sample_width, r


def record_to_file(path):
    """Records from the microphone and outputs the resulting data to 'path'"""
    sample_width, data = record()
    data = pack('<' + ('h'*len(data)), *data)

    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()


def split_and_cean(line, begin, delimiters):
    line = line.lstrip(begin).rstrip(";").strip("()")
    splits = line.split("|")
    splits = [split.strip() for split in splits]
    return splits


def get_number_from_words(sentence):
    # file = open('calculator.jsgf', mode='r')
    #file_lines = file.readlines()

    operations = ['плюс', 'минус', 'умножить на', 'разделить на']
    digits = ['ноль', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']

    splits = sentence.split(' ')

    operation = [operation for operation in operations if operation in splits][0]
    first = digits.index(splits[0])
    second = digits.index(splits[2])

    return {
        'плюс': first + second,
        'минус': first - second,
    }[operation]


    # for line in file_lines:
    #     if line.startswith('<operation>'):
    #         operations = split_and_cean(line, "<operation> = ", '|')
    #     if line.startswith('<n1>'):
    #         digits = split_and_cean(line, '<n1> = ')

if __name__ == '__main__':
    #print("please speak a word into the microphone")
    record_to_file('6.wav')
    #return_code = call("pocketsphinx_continuous -hmm sphinx_models_ru/model_ru/ -dict sphinx_models_ru/ru.dic -jsgf calculator.jsgf -infile demo.wav", shell=True)
    #sentence = "один плюс два"
    #result = get_number_from_words(sentence)
    #print(result)
    print("done - result written to demo.wav")
